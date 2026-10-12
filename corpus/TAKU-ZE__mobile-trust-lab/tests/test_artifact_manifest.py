from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.package_artifacts import SCHEMA, package_artifacts  # noqa: E402


class ArtifactManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.input = self.root / "input"
        self.output = self.root / "dist"
        self.input.mkdir()

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def write_apk(self, name: str, content: bytes) -> Path:
        path = self.input / name
        path.write_bytes(content)
        return path

    def test_packages_apks_in_stable_name_order(self) -> None:
        self.write_apk("vulnerable.apk", b"vulnerable fixture")
        self.write_apk("hardened.apk", b"hardened fixture")

        manifest = package_artifacts(self.input, self.output)

        self.assertEqual(manifest["schema"], SCHEMA)
        self.assertEqual(
            [item["name"] for item in manifest["files"]],
            ["hardened.apk", "vulnerable.apk"],
        )
        self.assertEqual((self.output / "hardened.apk").read_bytes(), b"hardened fixture")
        self.assertEqual((self.output / "vulnerable.apk").read_bytes(), b"vulnerable fixture")

    def test_text_and_json_checksums_match_artifact_bytes(self) -> None:
        content = b"deterministic apk bytes"
        self.write_apk("lab.apk", content)
        expected = hashlib.sha256(content).hexdigest()

        package_artifacts(self.input, self.output)

        self.assertEqual((self.output / "SHA256SUMS").read_text(), f"{expected}  lab.apk\n")
        parsed = json.loads((self.output / "build-manifest.json").read_text())
        self.assertEqual(parsed["files"][0]["sha256"], expected)
        self.assertEqual(parsed["files"][0]["size_bytes"], len(content))

    def test_repeated_packaging_is_deterministic(self) -> None:
        self.write_apk("lab.apk", b"same input")

        first = package_artifacts(self.input, self.output)
        first_json = (self.output / "build-manifest.json").read_bytes()
        second = package_artifacts(self.input, self.output)

        self.assertEqual(first, second)
        self.assertEqual((self.output / "build-manifest.json").read_bytes(), first_json)

    def test_non_apk_files_are_ignored_and_empty_input_is_rejected(self) -> None:
        (self.input / "notes.txt").write_text("not an artifact", encoding="utf-8")

        with self.assertRaises(FileNotFoundError):
            package_artifacts(self.input, self.output)


if __name__ == "__main__":
    unittest.main()
