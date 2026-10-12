from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .models import Finding

ANDROID_NS = "http://schemas.android.com/apk/res/android"
A = f"{{{ANDROID_NS}}}"


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _find_manifest(root: Path) -> Path:
    direct = root / "AndroidManifest.xml"
    if direct.is_file():
        return direct
    matches = sorted(root.rglob("AndroidManifest.xml"))
    if not matches:
        raise FileNotFoundError(f"No AndroidManifest.xml found under {root}")
    return matches[0]


def _is_launcher(component: ET.Element) -> bool:
    for intent_filter in component.findall("intent-filter"):
        actions = {
            node.get(A + "name", "") for node in intent_filter.findall("action")
        }
        categories = {
            node.get(A + "name", "") for node in intent_filter.findall("category")
        }
        if (
            "android.intent.action.MAIN" in actions
            and "android.intent.category.LAUNCHER" in categories
        ):
            return True
    return False


def _scan_manifest(manifest: Path, root: Path) -> list[Finding]:
    tree = ET.parse(manifest)
    document = tree.getroot()
    application = document.find("application")
    if application is None:
        return []

    source = _relative(manifest, root)
    findings: list[Finding] = []
    attribute_rules = (
        (
            "debuggable",
            "true",
            "MT-001",
            "Debuggable release application",
            "HIGH",
            "Set android:debuggable to false for release variants.",
        ),
        (
            "allowBackup",
            "true",
            "MT-002",
            "Application data backup is enabled",
            "MEDIUM",
            "Disable backup or define explicit data-extraction rules.",
        ),
        (
            "usesCleartextTraffic",
            "true",
            "MT-003",
            "Cleartext network traffic is allowed",
            "HIGH",
            "Require TLS and use a restrictive Network Security Config.",
        ),
    )
    for attribute, unsafe_value, rule_id, title, severity, remediation in attribute_rules:
        value = application.get(A + attribute, "").strip().lower()
        if value == unsafe_value:
            findings.append(
                Finding(
                    rule_id=rule_id,
                    title=title,
                    severity=severity,
                    evidence=f'android:{attribute}="{value}"',
                    remediation=remediation,
                    file=source,
                )
            )

    for component_type in ("activity", "service", "receiver", "provider"):
        for component in application.findall(component_type):
            if component.get(A + "exported", "").lower() != "true":
                continue
            if component_type == "activity" and _is_launcher(component):
                continue
            permission = component.get(A + "permission") or application.get(A + "permission")
            if permission:
                continue
            component_name = component.get(A + "name", "<unnamed>")
            findings.append(
                Finding(
                    rule_id="MT-004",
                    title=f"Unprotected exported {component_type}",
                    severity="HIGH",
                    evidence=f"{component_type} {component_name} is exported without a permission",
                    remediation="Set android:exported to false or enforce a signature-level permission.",
                    file=source,
                )
            )
    return findings


def _read_sources(root: Path) -> list[tuple[Path, str]]:
    sources: list[tuple[Path, str]] = []
    for suffix in ("*.java", "*.kt"):
        for path in sorted(root.rglob(suffix)):
            try:
                sources.append((path, path.read_text(encoding="utf-8")))
            except UnicodeDecodeError:
                continue
    return sources


def _scan_sources(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    sources = _read_sources(root)
    client_state_pattern = re.compile(
        r'(?i)(wallet[_-]?balance|player[_-]?level|premium[_-]?entitlement)'
    )
    reward_pattern = re.compile(r'(?i)reward[_-]?claimed')

    for path, text in sources:
        relative = _relative(path, root)
        if "getSharedPreferences" in text and client_state_pattern.search(text):
            findings.append(
                Finding(
                    rule_id="MT-005",
                    title="Client-authoritative state stored in SharedPreferences",
                    severity="HIGH",
                    evidence="Security-sensitive balance, level, or entitlement keys are locally authoritative.",
                    remediation="Move authoritative state to a trusted service; protect cached state with integrity metadata.",
                    file=relative,
                )
            )
        if "getSharedPreferences" in text and reward_pattern.search(text):
            findings.append(
                Finding(
                    rule_id="MT-006",
                    title="Replay-sensitive reward state is enforced only on the client",
                    severity="HIGH",
                    evidence="A local preference decides whether a reward may be claimed again.",
                    remediation="Enforce idempotency and replay protection at the authoritative boundary.",
                    file=relative,
                )
            )

    unique: dict[tuple[str, str], Finding] = {}
    for finding in findings:
        unique[(finding.rule_id, finding.file)] = finding
    return list(unique.values())


def scan_project(root: str | Path) -> list[Finding]:
    project_root = Path(root).resolve()
    if not project_root.is_dir():
        raise NotADirectoryError(project_root)
    manifest = _find_manifest(project_root)
    findings = _scan_manifest(manifest, project_root)
    findings.extend(_scan_sources(project_root))
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    return sorted(
        findings,
        key=lambda item: (severity_order.get(item.severity, 99), item.rule_id, item.file),
    )
