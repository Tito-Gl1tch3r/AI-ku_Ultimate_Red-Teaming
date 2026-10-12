"""Tests for hash validation and CSV reading in virusxcheck."""

import pytest
from virusxcheck import validate_hash, SHA256_PATTERN, read_csv


# --- validate_hash tests ---


class TestValidateHash:
    """Tests for the validate_hash function."""

    def test_valid_sha256(self):
        h = "a" * 64
        assert validate_hash(h) == "sha256"

    def test_valid_sha1(self):
        h = "b" * 40
        assert validate_hash(h) == "sha1"

    def test_valid_md5(self):
        h = "c" * 32
        assert validate_hash(h) == "md5"

    def test_valid_sha512(self):
        h = "d" * 128
        assert validate_hash(h) == "sha512"

    def test_mixed_case_hex(self):
        h = "aAbBcCdDeEfF" * 4 + "0123456789abcdef"
        assert len(h) == 64
        assert validate_hash(h) == "sha256"

    def test_all_digits(self):
        h = "1234567890" * 4 + "1234567890123456789012"
        assert len(h) == 62
        assert validate_hash(h) is None

    def test_realistic_sha256(self):
        h = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert validate_hash(h) == "sha256"

    def test_invalid_non_hex_chars(self):
        h = "g" * 64
        assert validate_hash(h) is None

    def test_invalid_special_chars(self):
        h = "!" * 64
        assert validate_hash(h) is None

    def test_invalid_length_63(self):
        h = "a" * 63
        assert validate_hash(h) is None

    def test_invalid_length_65(self):
        h = "a" * 65
        assert validate_hash(h) is None

    def test_invalid_length_31(self):
        h = "a" * 31
        assert validate_hash(h) is None

    def test_empty_string(self):
        assert validate_hash("") is None

    def test_spaces_in_hash(self):
        h = "a" * 32 + " " + "a" * 31
        assert validate_hash(h) is None

    def test_leading_trailing_spaces(self):
        h = " " + "a" * 64 + " "
        assert validate_hash(h) is None

    def test_sql_injection_attempt(self):
        assert validate_hash("' OR 1=1 --") is None

    def test_html_injection(self):
        assert validate_hash("<script>alert(1)</script>") is None

    def test_null_bytes(self):
        h = "a" * 32 + "\x00" + "a" * 31
        assert validate_hash(h) is None


# --- SHA256_PATTERN tests ---


class TestSHA256Pattern:
    """Tests for the SHA256_PATTERN compiled regex."""

    def test_matches_valid_sha256(self):
        h = "a" * 64
        assert SHA256_PATTERN.match(h) is not None

    def test_matches_mixed_case(self):
        h = "aAbBcCdDeEfF0123456789" * 2 + "aAbBcCdDeEfF01234567"
        assert len(h) == 64
        assert SHA256_PATTERN.match(h) is not None

    def test_rejects_63_chars(self):
        h = "a" * 63
        assert SHA256_PATTERN.match(h) is None

    def test_rejects_65_chars(self):
        h = "a" * 65
        assert SHA256_PATTERN.match(h) is None

    def test_rejects_non_hex(self):
        h = "g" * 64
        assert SHA256_PATTERN.match(h) is None

    def test_rejects_empty(self):
        assert SHA256_PATTERN.match("") is None

    def test_rejects_128_chars(self):
        h = "a" * 128
        assert SHA256_PATTERN.match(h) is None


# --- read_csv tests ---


class TestReadCsv:
    """Tests for the read_csv function."""

    def test_single_hash_column(self, tmp_path):
        csv_file = tmp_path / "hashes.csv"
        h = "a" * 64
        csv_file.write_text(f"hash\n{h}\n", encoding="utf-8")
        result = read_csv(str(csv_file))
        assert result == [h]

    def test_hash_in_second_column(self, tmp_path):
        csv_file = tmp_path / "hashes.csv"
        h = "b" * 64
        csv_file.write_text(f"name,hash\nmalware,{h}\n", encoding="utf-8")
        result = read_csv(str(csv_file))
        assert result == [h]

    def test_multiple_hashes_per_row(self, tmp_path):
        csv_file = tmp_path / "hashes.csv"
        h1 = "a" * 64
        h2 = "b" * 64
        # Only first match per cell is extracted, but two cells can each have one
        csv_file.write_text(f"hash1,hash2\n{h1},{h2}\n", encoding="utf-8")
        result = read_csv(str(csv_file))
        assert h1 in result
        assert h2 in result

    def test_multiple_rows(self, tmp_path):
        csv_file = tmp_path / "hashes.csv"
        h1 = "a" * 64
        h2 = "b" * 64
        h3 = "c" * 64
        csv_file.write_text(f"hash\n{h1}\n{h2}\n{h3}\n", encoding="utf-8")
        result = read_csv(str(csv_file))
        assert result == [h1, h2, h3]

    def test_no_valid_hashes(self, tmp_path):
        csv_file = tmp_path / "hashes.csv"
        csv_file.write_text("name,value\nfoo,bar\nbaz,123\n", encoding="utf-8")
        result = read_csv(str(csv_file))
        assert result == []

    def test_mixed_valid_invalid(self, tmp_path):
        csv_file = tmp_path / "hashes.csv"
        valid = "d" * 64
        csv_file.write_text(
            f"hash\nnotahash\n{valid}\ntooshort{'e' * 10}\n", encoding="utf-8"
        )
        result = read_csv(str(csv_file))
        assert result == [valid]

    def test_file_not_found_exits(self):
        with pytest.raises(SystemExit) as exc_info:
            read_csv("nonexistent_file_12345.csv")
        assert exc_info.value.code == 1

    def test_empty_file(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("", encoding="utf-8")
        result = read_csv(str(csv_file))
        assert result == []
