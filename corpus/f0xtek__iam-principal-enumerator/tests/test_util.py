import pytest
import string
from pathlib import Path
from unittest.mock import mock_open, patch
from iam_principal_enumerator.util import (
    generate_random_string,
    is_valid_file,
    read_lines_from_file,
)


def test_generate_random_string():
    length = 8
    random_string = generate_random_string(length)
    assert len(random_string) == length
    assert all(c in (string.ascii_letters + string.digits) for c in random_string)


def test_is_valid_file_exists():
    path = Path("/path/to/existing/file")
    with patch.object(Path, "is_file", return_value=True):
        assert is_valid_file(path) is True


def test_is_valid_file_not_exists():
    path = Path("/path/to/nonexistent/file")
    with patch.object(Path, "is_file", return_value=False):
        assert is_valid_file(path) is False


def test_read_lines_from_file():
    mock_file_content = "line1\nline2\nline3\n"
    path = Path("/path/to/file")
    with patch("builtins.open", mock_open(read_data=mock_file_content)):
        lines = list(read_lines_from_file(path))
        assert lines == ["line1", "line2", "line3"]
