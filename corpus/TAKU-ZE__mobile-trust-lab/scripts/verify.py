from __future__ import annotations

import io
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "auditor" / "src"))

from mobile_trust_audit.report import render_html, render_json, render_markdown
from mobile_trust_audit.scanner import scan_project


EXPECTED_RULES = {"MT-001", "MT-002", "MT-003", "MT-004", "MT-005", "MT-006"}


def run_tests() -> tuple[bool, int, int, str]:
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    failed = len(result.failures) + len(result.errors) + len(result.unexpectedSuccesses)
    return result.wasSuccessful(), result.testsRun - failed, result.testsRun, stream.getvalue()


def compare_reports(vulnerable: list, hardened: list) -> tuple[bool, int, list[str]]:
    generated = {
        "vulnerable.json": render_json(vulnerable),
        "vulnerable.md": render_markdown(vulnerable),
        "vulnerable.html": render_html(vulnerable),
        "hardened.json": render_json(hardened),
    }
    mismatches: list[str] = []
    for name, content in generated.items():
        checked_in = (ROOT / "sample-reports" / name).read_text(encoding="utf-8")
        if name.endswith(".json"):
            matches = json.loads(checked_in) == json.loads(content)
        else:
            matches = checked_in == content
        if not matches:
            mismatches.append(name)
    return not mismatches, len(generated), mismatches


def check_document_links() -> tuple[bool, int, list[str]]:
    markdown_files = [ROOT / "README.md", ROOT / "frida" / "README.md"]
    markdown_files.extend(sorted((ROOT / "docs").glob("*.md")))
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    checked = 0
    missing: list[str] = []
    for document in markdown_files:
        for target in pattern.findall(document.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            relative_target = target.split("#", 1)[0]
            if not relative_target:
                continue
            checked += 1
            if not (document.parent / relative_target).resolve().exists():
                source = document.relative_to(ROOT).as_posix()
                missing.append(f"{source} -> {target}")
    return not missing, checked, missing


def main() -> int:
    tests_ok, tests_passed, tests_run, test_log = run_tests()
    vulnerable = scan_project(ROOT / "fixtures" / "vulnerable")
    hardened = scan_project(ROOT / "fixtures" / "hardened")
    reports_ok, report_count, mismatches = compare_reports(vulnerable, hardened)
    links_ok, link_count, missing_links = check_document_links()

    vulnerable_rules = {finding.rule_id for finding in vulnerable}
    result_ok = (
        tests_ok
        and vulnerable_rules == EXPECTED_RULES
        and len(vulnerable) == 6
        and len(hardened) == 0
        and reports_ok
        and links_ok
    )

    print(f"Scanner tests: {'PASS' if tests_ok else 'FAIL'} ({tests_passed}/{tests_run})")
    print(f"Vulnerable findings: {len(vulnerable)}")
    print(f"Hardened findings: {len(hardened)}")
    report_status = "REPRODUCIBLE" if reports_ok else "MISMATCH"
    print(f"Sample reports: {report_status} ({report_count - len(mismatches)}/{report_count})")
    print(f"Documentation links: {'VALID' if links_ok else 'BROKEN'} ({link_count - len(missing_links)}/{link_count})")
    print(f"Result: {'PASS' if result_ok else 'FAIL'}")

    if not tests_ok:
        print("\nTest details:\n" + test_log, file=sys.stderr)
    if vulnerable_rules != EXPECTED_RULES:
        print(f"Unexpected vulnerable rule set: {sorted(vulnerable_rules)}", file=sys.stderr)
    if mismatches:
        print(f"Report mismatches: {', '.join(mismatches)}", file=sys.stderr)
    if missing_links:
        print("Broken documentation links: " + "; ".join(missing_links), file=sys.stderr)
    return 0 if result_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
