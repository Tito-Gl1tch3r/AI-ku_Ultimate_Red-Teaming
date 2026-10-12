import json
import sqlite3

from database.models import init_db
from database.repository import ScanRepository


def _insert_semgrep_scan(cursor, slug, version, status, summary):
    cursor.execute(
        "INSERT INTO semgrep_scans (slug, version, status, summary_json) VALUES (?, ?, ?, ?)",
        (slug, version, status, json.dumps(summary)),
    )
    return cursor.lastrowid


def _insert_semgrep_finding(cursor, scan_id, rule_id, message):
    cursor.execute(
        """
        INSERT INTO semgrep_findings (
            scan_id, rule_id, message, severity, file_path, line_number, code_snippet, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            scan_id,
            rule_id,
            message,
            "ERROR",
            "plugin/file.php",
            12,
            "dangerous_call();",
            json.dumps({}),
        ),
    )


def test_get_semgrep_scan_returns_latest_scan_by_id_with_its_findings(tmp_path):
    db_path = tmp_path / "semgrep_repo.db"
    init_db(db_path)
    repo = ScanRepository(db_path=db_path)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        older_scan_id = _insert_semgrep_scan(
            cursor,
            "hello-dolly",
            "1.0.0",
            "completed",
            {"total_findings": 0, "breakdown": {}},
        )
        newer_scan_id = _insert_semgrep_scan(
            cursor,
            "hello-dolly",
            "1.0.1",
            "completed",
            {"total_findings": 1, "breakdown": {"ERROR": 1}},
        )
        _insert_semgrep_finding(cursor, newer_scan_id, "wp.audit.test", "Latest finding")
        conn.commit()

    result = repo.get_semgrep_scan("hello-dolly")

    assert result is not None
    assert result["id"] == newer_scan_id
    assert result["version"] == "1.0.1"
    assert result["summary"] == {"total_findings": 1, "breakdown": {"ERROR": 1}}
    assert [finding["rule_id"] for finding in result["findings"]] == ["wp.audit.test"]
    assert older_scan_id != newer_scan_id
