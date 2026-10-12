"""Rotate identity — new Tor circuit + new User-Agent."""

from __future__ import annotations

import structlog

from tengu.stealth import get_stealth_layer
from tengu.tools.stealth.tor_new_identity import tor_new_identity

logger = structlog.get_logger(__name__)


async def rotate_identity(
    tor_control_port: int = 9051,
    tor_control_password: str = "",
) -> dict:
    """Rotate identity: request new Tor circuit and rotate User-Agent.

    Args:
        tor_control_port: Tor control port (default 9051)
        tor_control_password: Tor control password

    Returns:
        Dictionary with tor_rotated, new_user_agent, status.
    """
    stealth = get_stealth_layer()

    # Request new Tor circuit
    tor_result = await tor_new_identity(
        control_port=tor_control_port,
        control_password=tor_control_password,
    )

    # Rotate User-Agent
    new_ua = stealth.get_user_agent()
    if new_ua is None:
        new_ua = "UA rotation not enabled (set stealth.user_agent.enabled = true)"

    return {
        "tor_rotated": tor_result.get("success", False),
        "tor_message": tor_result.get("message", ""),
        "new_user_agent": new_ua,
        "status": "success" if tor_result.get("success") else "partial",
    }
