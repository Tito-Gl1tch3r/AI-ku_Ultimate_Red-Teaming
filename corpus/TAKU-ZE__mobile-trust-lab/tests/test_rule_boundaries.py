from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "auditor" / "src"))

from mobile_trust_audit.scanner import scan_project  # noqa: E402


class ProjectFixture:
    def __init__(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)

    def close(self) -> None:
        self._temporary.cleanup()

    def manifest(self, attributes: str = "", components: str = "", nested: bool = False) -> Path:
        destination = self.root / "app" / "src" / "main" if nested else self.root
        destination.mkdir(parents=True, exist_ok=True)
        path = destination / "AndroidManifest.xml"
        path.write_text(
            "\n".join(
                [
                    '<manifest xmlns:android="http://schemas.android.com/apk/res/android"',
                    '    package="com.takuze.boundaryfixture">',
                    f"    <application {attributes}>",
                    components,
                    "    </application>",
                    "</manifest>",
                ]
            ),
            encoding="utf-8",
        )
        return path

    def source(self, text: str, suffix: str = ".java", name: str = "StateStore") -> Path:
        path = self.root / "src" / f"{name}{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


class RuleBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = ProjectFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def rule_ids(self) -> list[str]:
        return [finding.rule_id for finding in scan_project(self.fixture.root)]

    def test_debuggable_true_only_reports_mt001(self) -> None:
        self.fixture.manifest(
            'android:debuggable="true" android:allowBackup="false" '
            'android:usesCleartextTraffic="false"'
        )
        self.assertEqual(self.rule_ids(), ["MT-001"])

    def test_backup_true_only_reports_mt002(self) -> None:
        self.fixture.manifest(
            'android:debuggable="false" android:allowBackup="true" '
            'android:usesCleartextTraffic="false"'
        )
        self.assertEqual(self.rule_ids(), ["MT-002"])

    def test_cleartext_true_only_reports_mt003(self) -> None:
        self.fixture.manifest(
            'android:debuggable="false" android:allowBackup="false" '
            'android:usesCleartextTraffic="true"'
        )
        self.assertEqual(self.rule_ids(), ["MT-003"])

    def test_safe_or_omitted_application_attributes_do_not_report(self) -> None:
        self.fixture.manifest()
        self.assertEqual(self.rule_ids(), [])

    def test_unprotected_exported_service_reports_mt004(self) -> None:
        self.fixture.manifest(
            components=(
                '        <service android:name=".SyncService" '
                'android:exported="true" />'
            )
        )
        findings = scan_project(self.fixture.root)
        self.assertEqual([finding.rule_id for finding in findings], ["MT-004"])
        self.assertIn("service .SyncService", findings[0].evidence)

    def test_launcher_activity_is_not_treated_as_admin_exposure(self) -> None:
        self.fixture.manifest(
            components="""        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>"""
        )
        self.assertEqual(self.rule_ids(), [])

    def test_component_permission_suppresses_mt004(self) -> None:
        self.fixture.manifest(
            components=(
                '        <receiver android:name=".AdminReceiver" android:exported="true" '
                'android:permission="com.takuze.boundaryfixture.ADMIN" />'
            )
        )
        self.assertEqual(self.rule_ids(), [])

    def test_application_permission_suppresses_mt004(self) -> None:
        self.fixture.manifest(
            attributes='android:permission="com.takuze.boundaryfixture.INTERNAL"',
            components='        <provider android:name=".DataProvider" android:exported="true" />',
        )
        self.assertEqual(self.rule_ids(), [])

    def test_non_exported_component_does_not_report(self) -> None:
        self.fixture.manifest(
            components='        <activity android:name=".AdminActivity" android:exported="false" />'
        )
        self.assertEqual(self.rule_ids(), [])

    def test_sensitive_shared_preferences_keys_report_mt005(self) -> None:
        self.fixture.manifest()
        self.fixture.source(
            """class StateStore {
    void save(android.content.Context context) {
        context.getSharedPreferences("state", 0).edit()
            .putInt("wallet_balance", 100).apply();
    }
}"""
        )
        self.assertEqual(self.rule_ids(), ["MT-005"])

    def test_sensitive_key_without_shared_preferences_does_not_report(self) -> None:
        self.fixture.manifest()
        self.fixture.source('class StateStore { String label = "wallet_balance"; }')
        self.assertEqual(self.rule_ids(), [])

    def test_shared_preferences_without_sensitive_key_does_not_report(self) -> None:
        self.fixture.manifest()
        self.fixture.source(
            'class Settings { void save(android.content.Context c) '
            '{ c.getSharedPreferences("ui", 0).edit().putBoolean("dark_mode", true).apply(); } }'
        )
        self.assertEqual(self.rule_ids(), [])

    def test_reward_preference_reports_mt006(self) -> None:
        self.fixture.manifest()
        self.fixture.source(
            'class Reward { void save(android.content.Context c) '
            '{ c.getSharedPreferences("state", 0).edit().putBoolean("reward_claimed", true).apply(); } }'
        )
        self.assertEqual(self.rule_ids(), ["MT-006"])

    def test_kotlin_source_is_scanned(self) -> None:
        self.fixture.manifest()
        self.fixture.source(
            """class StateStore(private val context: android.content.Context) {
    fun save() = context.getSharedPreferences("state", 0).edit()
        .putInt("player_level", 10)
        .putBoolean("reward-claimed", true)
        .apply()
}""",
            suffix=".kt",
        )
        self.assertEqual(self.rule_ids(), ["MT-005", "MT-006"])

    def test_multiple_sensitive_keys_in_one_file_are_deduplicated(self) -> None:
        self.fixture.manifest()
        self.fixture.source(
            """class StateStore {
    void save(android.content.Context c) {
        c.getSharedPreferences("state", 0).edit()
            .putInt("wallet_balance", 100)
            .putInt("player_level", 2)
            .putBoolean("premium_entitlement", true)
            .apply();
    }
}"""
        )
        self.assertEqual(self.rule_ids(), ["MT-005"])

    def test_nested_manifest_is_discovered(self) -> None:
        manifest = self.fixture.manifest('android:debuggable="true"', nested=True)
        findings = scan_project(self.fixture.root)
        self.assertEqual([finding.rule_id for finding in findings], ["MT-001"])
        self.assertEqual(findings[0].file, manifest.relative_to(self.fixture.root).as_posix())

    def test_missing_manifest_raises_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            scan_project(self.fixture.root)

    def test_non_utf8_source_is_skipped_without_hiding_manifest_findings(self) -> None:
        self.fixture.manifest('android:allowBackup="true"')
        source = self.fixture.root / "src" / "Invalid.java"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"\xff\xfe\x00\x00")
        self.assertEqual(self.rule_ids(), ["MT-002"])


if __name__ == "__main__":
    unittest.main()
