import csv
import json
import os
import platform
import stat

import pytest

from virusxcheck import (
    write_to_csv,
    write_to_json,
    update_env_file,
    update_env_file_multiple,
)

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

EXPECTED_CSV_HEADERS = [
    "Hash", "VX Status", "File Type", "Size", "First Seen",
    "Names", "VX URL", "Download Link", "VirusTotal URL",
    "VT Detection Rate", "VT Malicious", "VT Suspicious", "VT Clean",
    "VT Type", "VT First Seen", "VT Tags",
]


def _sample_data():
    """Return a minimal results dict with one hash entry."""
    return {
        "abc123": {
            "status": "Found in VX database",
            "details": {
                "type": "PE32",
                "size": "1024",
                "first_seen": "2024-01-01",
                "names": ["malware.exe"],
                "download_link": "https://example.com/dl",
            },
            "vx_url": "https://example.com/vx",
            "virustotal_url": "https://virustotal.com/abc123",
        }
    }


def _sample_data_with_vt():
    """Return results that include VirusTotal analysis data."""
    data = _sample_data()
    data["abc123"]["vt_data"] = {
        "last_analysis_stats": {
            "malicious": 30,
            "suspicious": 2,
            "undetected": 68,
        },
        "type_description": "Win32 EXE",
        "first_submission_date": "2023-06-15",
        "tags": ["peexe", "overlay"],
    }
    return data


def _read_csv_rows(path):
    """Read a CSV file and return (headers, data_rows)."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    return rows[0], rows[1:]


# ---------------------------------------------------------------------------
# write_to_csv tests
# ---------------------------------------------------------------------------

class TestWriteToCsv:

    def test_correct_headers(self, tmp_path):
        out = tmp_path / "results.csv"
        write_to_csv(str(out), _sample_data())
        headers, _ = _read_csv_rows(out)
        assert headers == EXPECTED_CSV_HEADERS

    def test_writes_hash_and_status(self, tmp_path):
        out = tmp_path / "results.csv"
        write_to_csv(str(out), _sample_data())
        _, rows = _read_csv_rows(out)
        assert len(rows) == 1
        row = rows[0]
        assert row[0] == "abc123"
        assert row[1] == "Found in VX database"

    def test_includes_vt_data(self, tmp_path):
        out = tmp_path / "results.csv"
        write_to_csv(str(out), _sample_data_with_vt())
        _, rows = _read_csv_rows(out)
        row = rows[0]
        # VT Detection Rate column (index 9)
        assert row[9] != "N/A"
        # VT Malicious (index 10)
        assert row[10] == "30"
        # VT Type (index 13)
        assert row[13] == "Win32 EXE"

    def test_empty_results(self, tmp_path):
        out = tmp_path / "results.csv"
        write_to_csv(str(out), {})
        headers, rows = _read_csv_rows(out)
        assert headers == EXPECTED_CSV_HEADERS
        assert rows == []


# ---------------------------------------------------------------------------
# write_to_json tests
# ---------------------------------------------------------------------------

class TestWriteToJson:

    def test_writes_valid_json(self, tmp_path):
        out = tmp_path / "results.json"
        write_to_json(str(out), _sample_data())
        with open(out, encoding="utf-8") as f:
            data = json.load(f)  # raises on invalid JSON
        assert isinstance(data, dict)

    def test_content_matches_input(self, tmp_path):
        out = tmp_path / "results.json"
        original = _sample_data()
        write_to_json(str(out), original)
        with open(out, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == original

    def test_handles_empty_dict(self, tmp_path):
        out = tmp_path / "results.json"
        write_to_json(str(out), {})
        with open(out, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == {}


# ---------------------------------------------------------------------------
# update_env_file tests
# ---------------------------------------------------------------------------

class TestUpdateEnvFile:

    def test_creates_new_env_file(self, tmp_path, monkeypatch):
        # Point the function at tmp_path by patching os.path.abspath(__file__)
        monkeypatch.setattr(
            "virusxcheck.os.path.abspath",
            lambda p: str(tmp_path / "virusxcheck.py"),
        )
        update_env_file("test_key_123")
        env_file = tmp_path / ".env"
        assert env_file.exists()
        content = env_file.read_text()
        assert "VIRUSXCHECK_API_KEY=test_key_123" in content

    def test_updates_existing_key(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "virusxcheck.os.path.abspath",
            lambda p: str(tmp_path / "virusxcheck.py"),
        )
        env_file = tmp_path / ".env"
        env_file.write_text("VIRUSXCHECK_API_KEY=old_key\n")

        update_env_file("new_key_456")
        content = env_file.read_text()
        assert "VIRUSXCHECK_API_KEY=new_key_456" in content
        assert "old_key" not in content

    def test_preserves_other_content(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "virusxcheck.os.path.abspath",
            lambda p: str(tmp_path / "virusxcheck.py"),
        )
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_VAR=keep_me\nVIRUSXCHECK_API_KEY=old\n")

        update_env_file("replaced")
        content = env_file.read_text()
        assert "OTHER_VAR=keep_me" in content
        assert "VIRUSXCHECK_API_KEY=replaced" in content

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Unix file permissions are not applicable on Windows",
    )
    def test_file_permissions(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "virusxcheck.os.path.abspath",
            lambda p: str(tmp_path / "virusxcheck.py"),
        )
        update_env_file("secret")
        env_file = tmp_path / ".env"
        mode = os.stat(str(env_file)).st_mode
        assert mode & stat.S_IRUSR  # owner can read
        assert mode & stat.S_IWUSR  # owner can write
        assert not (mode & stat.S_IRGRP)  # group cannot read
        assert not (mode & stat.S_IROTH)  # others cannot read


# ---------------------------------------------------------------------------
# update_env_file_multiple tests
# ---------------------------------------------------------------------------

class TestUpdateEnvFileMultiple:

    def test_writes_multiple_keys(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "virusxcheck.os.path.abspath",
            lambda p: str(tmp_path / "virusxcheck.py"),
        )
        update_env_file_multiple({"KEY_A": "val_a", "KEY_B": "val_b"})
        content = (tmp_path / ".env").read_text()
        assert "KEY_A=val_a" in content
        assert "KEY_B=val_b" in content

    def test_updates_existing_and_adds_new(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "virusxcheck.os.path.abspath",
            lambda p: str(tmp_path / "virusxcheck.py"),
        )
        env_file = tmp_path / ".env"
        env_file.write_text("KEY_A=old_a\n")

        update_env_file_multiple({"KEY_A": "new_a", "KEY_C": "val_c"})
        content = env_file.read_text()
        assert "KEY_A=new_a" in content
        assert "old_a" not in content
        assert "KEY_C=val_c" in content
