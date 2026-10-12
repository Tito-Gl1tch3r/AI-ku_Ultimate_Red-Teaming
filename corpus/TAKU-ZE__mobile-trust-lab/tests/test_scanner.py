from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "auditor" / "src"))

from mobile_trust_audit.report import render_json, render_markdown  # noqa: E402
from mobile_trust_audit.scanner import scan_project  # noqa: E402


class ScannerTests(unittest.TestCase):
    def test_vulnerable_fixture_exposes_expected_trust_failures(self) -> None:
        findings = scan_project(ROOT / "fixtures" / "vulnerable")
        self.assertEqual(
            {finding.rule_id for finding in findings},
            {"MT-001", "MT-002", "MT-003", "MT-004", "MT-005", "MT-006"},
        )
        self.assertEqual(len(findings), 6)

    def test_hardened_fixture_has_no_findings(self) -> None:
        self.assertEqual(scan_project(ROOT / "fixtures" / "hardened"), [])

    def test_real_app_variants_match_the_fixture_result(self) -> None:
        vulnerable = scan_project(ROOT / "lab-app" / "vulnerable")
        hardened = scan_project(ROOT / "lab-app" / "hardened")
        self.assertEqual(len(vulnerable), 6)
        self.assertEqual(hardened, [])

    def test_json_report_has_stable_schema(self) -> None:
        findings = scan_project(ROOT / "fixtures" / "vulnerable")
        report = json.loads(render_json(findings))
        self.assertEqual(report["schema"], "mobile-trust-audit/v1")
        self.assertEqual(report["summary"], {"HIGH": 5, "MEDIUM": 1})
        self.assertEqual(len(report["findings"]), 6)

    def test_markdown_report_contains_evidence_and_remediation(self) -> None:
        report = render_markdown(scan_project(ROOT / "fixtures" / "vulnerable"))
        self.assertIn("MT-004: Unprotected exported activity", report)
        self.assertIn("Remediation", report)


if __name__ == "__main__":
    unittest.main()
