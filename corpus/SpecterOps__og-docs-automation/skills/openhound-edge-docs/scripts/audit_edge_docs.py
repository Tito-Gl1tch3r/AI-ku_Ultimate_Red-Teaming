#!/usr/bin/env python3
"""Audit OpenHound edge docs for quality gates used by the openhound-edge-docs skill."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_SECTIONS = [
    "## Abuse Info",
    "## Opsec Considerations",
    "## References",
]

REVERSAL_HEADING = "### Reverting Abuse Actions"
TOP_LEVEL_REVERSAL_HEADING = "## Reverting Abuse Actions"
OBSOLETE_CLEANUP_HEADING = "## Cleanup after Abuse"

UI_REVERSAL_HEADINGS = [
    "Revert using Admin Console:",
    "Revert using Web UI:",
    "Revert using GitHub UI:",
    "Revert using Jamf Pro:",
    "Revert using Console:",
    "Revert using source system:",
]

OFFICIAL_DOC_RE = re.compile(
    r"https?://(?:"
    r"developer\.okta\.com|help\.okta\.com|"
    r"docs\.github\.com|api\.github\.com|"
    r"developer\.jamf\.com|learn\.jamf\.com|help\.jamf\.com|docs\.jamf\.com|"
    r"support\.apple\.com|developer\.apple\.com|"
    r"[^/]*\.microsoft\.com|docs\."
    r")"
)

GENERIC_REVERSAL_PATTERNS = [
    "Reversal should restore the affected objects",
    "restore the affected objects to their pre-abuse state",
    "remove any temporary access, sessions, credentials, or synchronization changes",
]


def section(text: str, heading: str) -> str:
    heading_level = len(heading) - len(heading.lstrip("#"))
    pattern = re.compile(
        rf"^{re.escape(heading)}\n(?P<body>.*?)(?=^#{{1,{heading_level}}} |\Z)",
        re.M | re.S,
    )
    match = pattern.search(text)
    return match.group("body") if match else ""


def ordered_sections(text: str) -> bool:
    positions: list[int] = []
    for heading in REQUIRED_SECTIONS:
        pos = text.find(heading)
        if pos == -1:
            return False
        positions.append(pos)
    return positions == sorted(positions)


def audit_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    issues: list[str] = []

    for heading in REQUIRED_SECTIONS:
        if heading not in text:
            issues.append(f"missing required section {heading!r}")

    if all(heading in text for heading in REQUIRED_SECTIONS) and not ordered_sections(text):
        issues.append("required sections are not in expected order")

    abuse = section(text, "## Abuse Info")
    reversal = section(text, REVERSAL_HEADING)
    reversal_headings = re.findall(rf"^{re.escape(REVERSAL_HEADING)}$", text, re.M)

    if re.search(rf"^{re.escape(TOP_LEVEL_REVERSAL_HEADING)}$", text, re.M):
        issues.append(
            "reversal must be an optional '### Reverting Abuse Actions' subsection "
            "inside '## Abuse Info', not a top-level section"
        )

    if re.search(rf"^{re.escape(OBSOLETE_CLEANUP_HEADING)}$", text, re.M):
        issues.append(
            "replace the obsolete cleanup section with an optional "
            "'### Reverting Abuse Actions' subsection when reversal is warranted, "
            "or remove it when the abuse changes no state"
        )

    if reversal_headings:
        if len(reversal_headings) > 1:
            issues.append("multiple reversal subsections found")
        if REVERSAL_HEADING not in abuse:
            issues.append("reversal subsection must be inside '## Abuse Info'")
        if not any(heading in reversal for heading in UI_REVERSAL_HEADINGS):
            issues.append("reversal missing UI/Admin Console reversal heading")
        if "Revert using API:" not in reversal:
            issues.append("reversal missing 'Revert using API:'")
        first_para = reversal.strip().split("\n\n", 1)[0].strip()
        if not first_para:
            issues.append("reversal missing edge-specific summary before steps")
        if any(pattern in reversal for pattern in GENERIC_REVERSAL_PATTERNS):
            issues.append("reversal contains generic boilerplate")

    if abuse:
        abuse_steps = abuse.split(REVERSAL_HEADING, 1)[0]
        if len(re.findall(r"^\d+\. ", abuse_steps, re.M)) < 3:
            issues.append("abuse info has fewer than three numbered steps")

    refs = section(text, "## References")
    if refs:
        links = re.findall(r"https?://", refs)
        if not links:
            issues.append("references section has no links")
        if not OFFICIAL_DOC_RE.search(refs):
            issues.append("references do not appear to include official documentation")

    return issues


def iter_edge_docs(target: Path, prefix: str | None = None) -> list[Path]:
    if target.is_file():
        return [target]
    pattern = f"{prefix}*.md" if prefix else "*.md"
    return sorted(target.glob(pattern))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default="descriptions/edges")
    parser.add_argument(
        "--prefix",
        help="Optional edge filename prefix filter, for example Okta_, GH_, or jamf_.",
    )
    args = parser.parse_args()

    target = Path(args.target)
    files = iter_edge_docs(target, args.prefix)
    if not files:
        print(f"No edge docs found at {target}", file=sys.stderr)
        return 2

    failures = 0
    for path in files:
        issues = audit_file(path)
        if issues:
            failures += len(issues)
            print(path)
            for issue in issues:
                print(f"  - {issue}")

    if failures:
        print(f"\n{failures} issue(s) found across {len(files)} file(s).")
        return 1

    print(f"All {len(files)} edge doc(s) passed quality gates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
