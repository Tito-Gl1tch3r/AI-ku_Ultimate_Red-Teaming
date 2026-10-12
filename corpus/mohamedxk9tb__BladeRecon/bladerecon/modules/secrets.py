"""Informational secret pattern discovery for downloaded JavaScript."""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Tuple

from .utils import atomic_write_text, info, log_duration, prepare_module_output, print_module_summary, setup_logging, success, target_output_dir, warn, write_json

SECRET_PATTERNS: Tuple[Tuple[str, Pattern[str]], ...] = (
    ("Private Key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("AWS Access Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("AWS Secret Access Key", re.compile(r"(?i)\b(?:aws[_-]?secret[_-]?access[_-]?key|aws[_-]?secret|secretAccessKey)\b\s*[:=]\s*['\"](?P<secret>[A-Za-z0-9/+=]{40})['\"]")),
    ("Google API Key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("OpenAI API Key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b")),
    ("Stripe Key", re.compile(r"\b(?:sk|pk)_(?:live|test)_[0-9A-Za-z]{16,}\b")),
    ("JWT Token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("Bearer Token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}\b", re.IGNORECASE)),
    ("Webhook URL", re.compile(r"https://hooks\.(?:slack|discord)\.com/[A-Za-z0-9/_?=&.-]+", re.IGNORECASE)),
    ("Slack Token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("GitHub Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("GitHub Fine-Grained Token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}_[A-Za-z0-9_]{59,}\b")),
    ("GitLab Token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b")),
    ("SendGrid API Key", re.compile(r"\bSG\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b")),
    ("Mailgun API Key", re.compile(r"\bkey-[0-9a-f]{32}\b", re.IGNORECASE)),
    ("Generic API Key", re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret)\b\s*[:=]\s*['\"][A-Za-z0-9_\-./+=]{16,}['\"]")),
)


def _secret_confidence(secret_type: str) -> str:
    high = {
        "AWS Access Key",
        "Slack Token",
        "GitHub Token",
        "GitLab Token",
        "GitHub Fine-Grained Token",
        "OpenAI API Key",
        "Private Key",
        "JWT Token",
        "Webhook URL",
        "SendGrid API Key",
        "Mailgun API Key",
    }
    medium = {"AWS Secret Access Key", "Bearer Token", "Session Token", "OAuth Token", "Stripe Key"}
    if secret_type in high:
        return "HIGH"
    if secret_type in medium:
        return "MEDIUM"
    return "LOW"


def _secret_risk(secret_type: str, confidence: str) -> str:
    if confidence == "HIGH":
        return "High"
    if confidence == "MEDIUM":
        return "Medium"
    if "client" in secret_type.lower() or "analytics" in secret_type.lower() or "tracking" in secret_type.lower():
        return "Low"
    return "Low"


def _value_preview(value: str) -> str:
    clean = str(value or "").strip()
    if len(clean) <= 18:
        return clean
    return f"{clean[:8]}...{clean[-6:]}"


def _value_fingerprint(value: str) -> str:
    clean = str(value or "").strip()
    if not clean:
        return ""
    return hashlib.sha256(clean.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _redacted_finding(secret_type: str, value: str, confidence: Optional[str] = None, risk: Optional[str] = None) -> Dict[str, str]:
    resolved_confidence = str(confidence or _secret_confidence(secret_type)).upper()
    return {
        "type": secret_type,
        "value_preview": _value_preview(value),
        "value_fingerprint": _value_fingerprint(value),
        "redacted": "true",
        "confidence": resolved_confidence,
        "risk": str(risk or _secret_risk(secret_type, resolved_confidence)),
    }


def _load_js_rows(target_dir: Path) -> List[dict]:
    path = target_dir / "js" / "js_files.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _load_historical_secret_rows(target_dir: Path) -> List[dict]:
    path = target_dir / "historical_js" / "secrets.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _read_js_content(target_dir: Path, row: dict) -> str:
    local_path = str(row.get("local_path") or "")
    if not local_path:
        return ""
    path = target_dir / local_path
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_secrets(content: str) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    for secret_type, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(content):
            value = match.groupdict().get("secret") or match.group(0)
            confidence = _secret_confidence(secret_type)
            findings.append(_redacted_finding(secret_type, value, confidence))
    return findings


def run(domain: str, output: Path = Path("results"), resume: bool = False) -> List[Dict[str, str]]:
    """Scan downloaded JavaScript files for exposed secret patterns."""
    target_dir = target_output_dir(output, domain)
    out_dir = prepare_module_output(output, domain, "secrets", resume=resume)
    log = setup_logging(domain, output, "secrets")
    started = time.perf_counter()

    info(f"Secret discovery started for {domain}")
    rows = _load_js_rows(target_dir)
    if not rows:
        warn("No JavaScript inventory found. Run js before secrets.")

    findings: List[Dict[str, str]] = []
    seen = set()
    with log_duration(log, "secrets"):
        for row in rows:
            source_url = str(row.get("url") or "")
            content = _read_js_content(target_dir, row)
            if not content:
                continue
            for finding in _find_secrets(content):
                key = (
                    finding["type"],
                    finding.get("value_fingerprint") or finding.get("value_preview") or "",
                    source_url,
                )
                if key in seen:
                    continue
                seen.add(key)
                findings.append({**finding, "source": source_url})
        for row in _load_historical_secret_rows(target_dir):
            if not isinstance(row, dict):
                continue
            secret_type = str(row.get("type") or "")
            value = str(row.get("value") or row.get("value_preview") or "")
            source_url = str(row.get("source") or "historical_js")
            if not secret_type or not value:
                continue
            key = (secret_type, value, source_url)
            if key in seen:
                continue
            seen.add(key)
            confidence = str(row.get("confidence") or _secret_confidence(secret_type))
            finding = _redacted_finding(secret_type, value, confidence, str(row.get("risk") or ""))
            if row.get("value_preview"):
                finding["value_preview"] = str(row.get("value_preview"))
            finding.update({"source": source_url, "source_type": "historical_js"})
            findings.append(finding)

    atomic_write_text(
        out_dir / "secrets.txt",
        "\n".join(
            f"{item['type']} [{item.get('confidence', 'LOW')}]: {item.get('value_preview', '[redacted]')} ({item['source']})"
            for item in findings
        ),
        encoding="utf-8",
    )
    write_json(out_dir / "secrets.json", findings)
    write_json(
        out_dir / "metadata.json",
        {
            "js_files": len(rows),
            "historical_js_secret_rows": len(_load_historical_secret_rows(target_dir)),
            "findings": len(findings),
        },
    )

    success(f"Secrets detected: {len(findings)}")
    print_module_summary(
        "Secret Summary",
        {
            "Target": domain,
            "Duration": f"{time.perf_counter() - started:.2f}s",
            "JavaScript Files": len(rows),
            "Results Found": len(findings),
            "Output Location": out_dir,
        },
    )
    log.info("Secret discovery found %d findings", len(findings))
    return findings
