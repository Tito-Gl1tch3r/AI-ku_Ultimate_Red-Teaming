from __future__ import annotations

import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "capture_repository_evidence.py"
SPEC = importlib.util.spec_from_file_location("capture_repository_evidence", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RepositoryEvidenceTests(unittest.TestCase):
    def test_parse_verification_output(self) -> None:
        parsed = MODULE.parse_verification_output(
            "Scanner tests: PASS (39/39)\nDocumentation links: VALID (88/88)\nResult: PASS\n"
        )
        self.assertEqual(parsed["Scanner tests"], "PASS (39/39)")
        self.assertEqual(parsed["Result"], "PASS")

    def test_parse_ignores_non_summary_lines(self) -> None:
        parsed = MODULE.parse_verification_output("heading\nResult: FAIL\n")
        self.assertEqual(parsed, {"Result": "FAIL"})

    def test_sha256_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.txt"
            path.write_bytes(b"mobile-trust-lab\n")
            expected = hashlib.sha256(b"mobile-trust-lab\n").hexdigest()
            self.assertEqual(MODULE.sha256_file(path), expected)


if __name__ == "__main__":
    unittest.main()
