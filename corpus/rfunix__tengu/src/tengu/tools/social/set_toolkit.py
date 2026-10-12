"""Social Engineering Toolkit (SET) integration via seautomate.

CRITICAL: set_credential_harvester and set_payload_generator are destructive
operations that require explicit human authorization before execution.
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import structlog
from fastmcp import Context

from tengu.config import get_config
from tengu.executor.process import run_command
from tengu.executor.registry import resolve_tool_path
from tengu.security.allowlist import make_allowlist_from_config
from tengu.security.audit import get_audit_logger
from tengu.security.rate_limiter import rate_limited
from tengu.security.sanitizer import (
    sanitize_port_spec,
    sanitize_scan_type,
    sanitize_target,
    sanitize_url,
)

logger = structlog.get_logger(__name__)

_VALID_PAYLOAD_TYPES = ["powershell_alphanumeric", "powershell_reverse", "hta"]

# Maps payload_type to SET's "Create a Payload and Listener" sub-menu option number
_PAYLOAD_MENU_OPTIONS: dict[str, str] = {
    "powershell_alphanumeric": "1",
    "powershell_reverse": "2",
    "hta": "3",
}


def _build_answer_file(answers: list[str]) -> str:
    """Write SET menu answers to a temporary file for seautomate and return its path.

    Each entry in `answers` corresponds to one line in the answer file —
    either a menu selection number or a parameter value.
    """
    content = "\n".join(answers) + "\n"
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="tengu_set_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
    except Exception:
        Path(path).unlink(missing_ok=True)
        raise
    return path


async def set_credential_harvester(
    ctx: Context,
    target_url: str,
    lhost: str,
    listen_port: int = 80,
    timeout: int | None = None,
) -> dict:
    """Clone a website and capture credentials submitted via the phishing page.

    WARNING: This is a destructive operation intended for authorized phishing
    simulations and social engineering security assessments ONLY.
    Requires explicit human confirmation before execution.

    Uses SET's Website Attack Vectors → Credential Harvester → Site Cloner
    module via seautomate. The tool clones the specified URL and starts a
    local HTTP server that captures form submissions (credentials) and
    redirects victims to the legitimate site.

    Args:
        target_url: URL of the site to clone (must be in tengu.toml allowlist).
        lhost: Local IP address that will host the cloned page and receive captured
               credentials (the POST-back address embedded in the cloned form).
        listen_port: Local TCP port for the credential capture server (default: 80).
        timeout: Execution timeout in seconds (default: from config).

    Returns:
        Dict with tool name, target_url, lhost, listen_port, returncode,
        output (truncated to 5000 chars), errors (truncated to 2000 chars),
        and success flag.

    Note:
        REQUIRES HUMAN CONFIRMATION. This tool starts an active phishing server.
        Only execute with explicit written authorization from the target organization.
    """
    cfg = get_config()
    audit = get_audit_logger()
    effective_timeout = timeout or cfg.tools.defaults.scan_timeout
    params: dict[str, object] = {
        "target_url": target_url,
        "lhost": lhost,
        "listen_port": listen_port,
    }

    # Sanitize inputs
    target_url = sanitize_url(target_url)
    lhost = sanitize_target(lhost)
    sanitize_port_spec(str(listen_port))  # validates port range, not used in answer file

    # Allowlist check
    allowlist = make_allowlist_from_config()
    try:
        allowlist.check(target_url)
    except Exception as exc:
        await audit.log_target_blocked("set_credential_harvester", target_url, str(exc))
        raise

    # SET menu path: 1 (SE Attacks) → 2 (Website Attack) → 3 (Credential Harvester)
    #                → 2 (Site Cloner) → lhost → target_url
    answers = ["1", "2", "3", "2", lhost, target_url]
    answer_file = _build_answer_file(answers)

    seautomate_path = resolve_tool_path("seautomate", "")

    await ctx.report_progress(
        0, 100, f"Starting SET credential harvester targeting {target_url}..."
    )

    try:
        async with rate_limited("setoolkit"):
            start = time.monotonic()
            await audit.log_tool_call(
                "set_credential_harvester", target_url, params, result="started"
            )
            try:
                stdout, stderr, returncode = await run_command(
                    [seautomate_path, answer_file], timeout=effective_timeout
                )
            except Exception as exc:
                await audit.log_tool_call(
                    "set_credential_harvester",
                    target_url,
                    params,
                    result="failed",
                    error=str(exc),
                )
                raise
            duration = time.monotonic() - start
    finally:
        Path(answer_file).unlink(missing_ok=True)

    await audit.log_tool_call(
        "set_credential_harvester",
        target_url,
        params,
        result="completed",
        duration_seconds=duration,
    )
    await ctx.report_progress(100, 100, "Credential harvester started")

    return {
        "tool": "set_credential_harvester",
        "target_url": target_url,
        "lhost": lhost,
        "listen_port": listen_port,
        "returncode": returncode,
        "output": stdout[:5000] if stdout else "",
        "errors": stderr[:2000] if stderr else "",
        "success": returncode == 0,
    }


async def set_qrcode_attack(
    ctx: Context,
    url: str,
    timeout: int | None = None,
) -> dict:
    """Generate a QR code pointing to a malicious URL for physical social engineering.

    Uses SET's QRCode Generator Attack Vector via seautomate. The generated QR
    code can be printed and placed physically (badge lanyards, posters, signs) as
    part of a physical social engineering assessment to test user awareness.

    Args:
        url: The URL to encode in the QR code (must be in tengu.toml allowlist).
        timeout: Execution timeout in seconds (default: from config).

    Returns:
        Dict with tool name, url, returncode, output (truncated), errors, and
        success flag. The QR code image is written to SET's output directory.
    """
    cfg = get_config()
    audit = get_audit_logger()
    effective_timeout = timeout or cfg.tools.defaults.scan_timeout
    params: dict[str, object] = {"url": url}

    # Sanitize input
    url = sanitize_url(url)

    # Allowlist check
    allowlist = make_allowlist_from_config()
    try:
        allowlist.check(url)
    except Exception as exc:
        await audit.log_target_blocked("set_qrcode_attack", url, str(exc))
        raise

    # SET menu path: 1 (SE Attacks) → 9 (QRCode Generator) → url
    answers = ["1", "9", url]
    answer_file = _build_answer_file(answers)

    seautomate_path = resolve_tool_path("seautomate", "")

    await ctx.report_progress(0, 100, f"Generating QR code for {url}...")

    try:
        async with rate_limited("setoolkit"):
            start = time.monotonic()
            await audit.log_tool_call("set_qrcode_attack", url, params, result="started")
            try:
                stdout, stderr, returncode = await run_command(
                    [seautomate_path, answer_file], timeout=effective_timeout
                )
            except Exception as exc:
                await audit.log_tool_call(
                    "set_qrcode_attack", url, params, result="failed", error=str(exc)
                )
                raise
            duration = time.monotonic() - start
    finally:
        Path(answer_file).unlink(missing_ok=True)

    await audit.log_tool_call(
        "set_qrcode_attack", url, params, result="completed", duration_seconds=duration
    )
    await ctx.report_progress(100, 100, "QR code generated")

    return {
        "tool": "set_qrcode_attack",
        "url": url,
        "returncode": returncode,
        "output": stdout[:5000] if stdout else "",
        "errors": stderr[:2000] if stderr else "",
        "success": returncode == 0,
    }


async def set_payload_generator(
    ctx: Context,
    payload_type: str,
    lhost: str,
    lport: int,
    timeout: int | None = None,
) -> dict:
    """Generate a social engineering payload for use in authorized campaigns.

    WARNING: This is a destructive operation that generates executable payloads
    intended for authorized penetration tests and red team engagements ONLY.
    Requires explicit human confirmation before execution.

    Uses SET's "Create a Payload and Listener" module via seautomate to generate
    a payload that, when executed by a target, will establish a reverse connection
    to the operator's listener.

    Supported payload types:
        - powershell_alphanumeric: PowerShell shellcode injector (alphanumeric)
        - powershell_reverse: PowerShell reverse shell
        - hta: HTML Application (HTA) attack

    Args:
        payload_type: Type of payload to generate. One of: powershell_alphanumeric,
                      powershell_reverse, hta.
        lhost: Attacker's IP address that the payload will connect back to.
        lport: TCP port on lhost that the listener will bind to.
        timeout: Execution timeout in seconds (default: from config).

    Returns:
        Dict with tool name, payload_type, lhost, lport, returncode,
        output (truncated to 5000 chars), errors (truncated to 2000 chars),
        and success flag.

    Note:
        REQUIRES HUMAN CONFIRMATION. Generates executable attack payloads.
        Only execute with explicit written authorization from the target organization.
    """
    cfg = get_config()
    audit = get_audit_logger()
    effective_timeout = timeout or cfg.tools.defaults.scan_timeout
    params: dict[str, object] = {
        "payload_type": payload_type,
        "lhost": lhost,
        "lport": lport,
    }

    # Sanitize inputs
    payload_type = sanitize_scan_type(payload_type, _VALID_PAYLOAD_TYPES, field="payload_type")
    lhost = sanitize_target(lhost)
    sanitize_port_spec(str(lport))  # validates port range

    # Allowlist check for lhost
    allowlist = make_allowlist_from_config()
    try:
        allowlist.check(lhost)
    except Exception as exc:
        await audit.log_target_blocked("set_payload_generator", lhost, str(exc))
        raise

    menu_option = _PAYLOAD_MENU_OPTIONS[payload_type]

    # SET menu path: 1 (SE Attacks) → 4 (Create a Payload and Listener)
    #                → {menu_option} → lhost → lport
    answers = ["1", "4", menu_option, lhost, str(lport)]
    answer_file = _build_answer_file(answers)

    seautomate_path = resolve_tool_path("seautomate", "")

    await ctx.report_progress(
        0, 100, f"Generating {payload_type} payload (LHOST={lhost} LPORT={lport})..."
    )

    try:
        async with rate_limited("setoolkit"):
            start = time.monotonic()
            await audit.log_tool_call("set_payload_generator", lhost, params, result="started")
            try:
                stdout, stderr, returncode = await run_command(
                    [seautomate_path, answer_file], timeout=effective_timeout
                )
            except Exception as exc:
                await audit.log_tool_call(
                    "set_payload_generator", lhost, params, result="failed", error=str(exc)
                )
                raise
            duration = time.monotonic() - start
    finally:
        Path(answer_file).unlink(missing_ok=True)

    await audit.log_tool_call(
        "set_payload_generator", lhost, params, result="completed", duration_seconds=duration
    )
    await ctx.report_progress(100, 100, "Payload generated")

    return {
        "tool": "set_payload_generator",
        "payload_type": payload_type,
        "lhost": lhost,
        "lport": lport,
        "returncode": returncode,
        "output": stdout[:5000] if stdout else "",
        "errors": stderr[:2000] if stderr else "",
        "success": returncode == 0,
    }
