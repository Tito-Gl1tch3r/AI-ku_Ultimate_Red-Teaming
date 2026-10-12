import zipfile
from pathlib import Path

import pytest

from kernagent.cli import _safe_extract_zip
from kernagent.snapshot import SnapshotError


def build_zip(target: Path, entries: dict[str, str]) -> None:
    with zipfile.ZipFile(target, "w") as zf:
        for name, contents in entries.items():
            zf.writestr(name, contents)


def test_safe_extract_allows_normal_entries(tmp_path):
    zip_path = tmp_path / "snapshot.zip"
    build_zip(zip_path, {"safe_dir/file.txt": "hello"})

    output_dir = tmp_path / "output"
    _safe_extract_zip(zip_path, output_dir)

    extracted = output_dir / "safe_dir" / "file.txt"
    assert extracted.read_text() == "hello"


@pytest.mark.parametrize("entry_name", ["../escape.txt", "/abs/path.txt", r"C:\\evil.txt"])
def test_safe_extract_blocks_unsafe_members(tmp_path, entry_name):
    zip_path = tmp_path / "malicious.zip"
    build_zip(zip_path, {entry_name: "oops"})

    output_dir = tmp_path / "output"
    with pytest.raises(SnapshotError):
        _safe_extract_zip(zip_path, output_dir)
