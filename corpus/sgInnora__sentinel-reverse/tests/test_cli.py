# -*- coding: utf-8 -*-
"""Tests for sentinel-reverse CLI and format detection."""

import json
import struct
import tempfile
import os
import pytest

from sentinel_reverse.cli import (
    detect_binary_format,
    discover_models,
    ANALYSIS_MODES,
    CheckpointManager,
    build_parser,
)


class TestBinaryFormatDetection:
    """Test binary format detection from magic bytes."""

    def _write_binary(self, header: bytes, size: int = 1024) -> str:
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".bin")
        f.write(header)
        f.write(b"\x00" * (size - len(header)))
        f.close()
        return f.name

    def test_detect_elf(self):
        path = self._write_binary(b"\x7fELF\x02")
        try:
            result = detect_binary_format(path)
            assert result["format"] == "ELF"
            assert result["arch"] == "x86_64"
        finally:
            os.unlink(path)

    def test_detect_elf_32bit(self):
        path = self._write_binary(b"\x7fELF\x01")
        try:
            result = detect_binary_format(path)
            assert result["format"] == "ELF"
            assert result["arch"] == "x86"
        finally:
            os.unlink(path)

    def test_detect_pe(self):
        # Minimal PE header
        header = b"MZ" + b"\x00" * 58
        # PE offset at 0x3C pointing to 0x80
        header += struct.pack("<I", 0x80)
        header += b"\x00" * (0x80 - len(header))
        header += b"PE\x00\x00"
        # COFF header (20 bytes)
        header += b"\x00" * 20
        # Optional header magic: PE32+ (0x020B)
        header += b"\x0b\x02"
        path = self._write_binary(header, size=2048)
        try:
            result = detect_binary_format(path)
            assert "PE" in result["format"]
            assert "64-bit" in result["format"] or "PE32+" in result["format"]
        finally:
            os.unlink(path)

    def test_detect_macho_64(self):
        path = self._write_binary(b"\xcf\xfa\xed\xfe")
        try:
            result = detect_binary_format(path)
            assert "Mach-O" in result["format"]
            assert "64" in result["format"]
        finally:
            os.unlink(path)

    def test_detect_apk(self):
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".apk")
        f.write(b"PK\x03\x04")
        f.write(b"\x00" * 1020)
        f.close()
        try:
            result = detect_binary_format(f.name)
            assert result["format"] == "APK (Android)"
            assert result["is_apk"] is True
        finally:
            os.unlink(f.name)

    def test_detect_dex(self):
        path = self._write_binary(b"dex\n035\x00")
        try:
            result = detect_binary_format(path)
            assert result["format"] == "DEX"
        finally:
            os.unlink(path)

    def test_detect_unknown(self):
        path = self._write_binary(b"\x00\x00\x00\x00")
        try:
            result = detect_binary_format(path)
            assert result["format"] == "Unknown"
        finally:
            os.unlink(path)

    def test_result_has_all_fields(self):
        path = self._write_binary(b"\x7fELF\x02")
        try:
            result = detect_binary_format(path)
            assert "format" in result
            assert "arch" in result
            assert "size" in result
            assert "size_mb" in result
            assert "filename" in result
            assert "extension" in result
        finally:
            os.unlink(path)


class TestAnalysisModes:
    """Test analysis mode configurations."""

    def test_all_modes_exist(self):
        assert "quick" in ANALYSIS_MODES
        assert "standard" in ANALYSIS_MODES
        assert "exhaustive" in ANALYSIS_MODES
        assert "security" in ANALYSIS_MODES

    def test_mode_fields(self):
        for name, mode in ANALYSIS_MODES.items():
            assert "confidence_threshold" in mode, f"{name} missing threshold"
            assert "max_rounds" in mode, f"{name} missing max_rounds"
            assert "max_functions" in mode, f"{name} missing max_functions"
            assert "temperature" in mode, f"{name} missing temperature"
            assert "max_tokens" in mode, f"{name} missing max_tokens"

    def test_quick_is_fastest(self):
        assert ANALYSIS_MODES["quick"]["max_rounds"] < ANALYSIS_MODES["standard"]["max_rounds"]
        assert ANALYSIS_MODES["quick"]["confidence_threshold"] < ANALYSIS_MODES["standard"]["confidence_threshold"]

    def test_exhaustive_is_most_thorough(self):
        assert ANALYSIS_MODES["exhaustive"]["max_rounds"] >= 15
        assert ANALYSIS_MODES["exhaustive"]["confidence_threshold"] >= 0.90
        assert ANALYSIS_MODES["exhaustive"]["max_functions"] >= 9999


class TestCheckpointManager:
    """Test checkpoint save/load/clear."""

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CheckpointManager(tmpdir, "test_binary")
            cm.save(2, {"binary_info": {"functions": []}})
            loaded = cm.load()
            assert loaded is not None
            assert loaded["phase"] == 2
            assert "timestamp" in loaded
            assert loaded["data"]["binary_info"]["functions"] == []

    def test_exists_property(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CheckpointManager(tmpdir, "test_binary")
            assert cm.exists is False
            cm.save(1, {})
            assert cm.exists is True

    def test_clear(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CheckpointManager(tmpdir, "test_binary")
            cm.save(1, {"data": "test"})
            assert cm.exists is True
            cm.clear()
            assert cm.exists is False

    def test_load_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CheckpointManager(tmpdir, "nonexistent")
            assert cm.load() is None


class TestModelDiscovery:
    """Test MLX model auto-discovery."""

    def test_discover_returns_list(self):
        result = discover_models()
        assert isinstance(result, list)

    def test_discover_with_mock_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = os.path.join(tmpdir, "test-model-4bit")
            os.makedirs(model_dir)
            # Create fake config.json
            config = {"model_type": "llama", "vocab_size": 32000, "hidden_size": 4096}
            with open(os.path.join(model_dir, "config.json"), "w") as f:
                json.dump(config, f)
            # Create fake weights
            with open(os.path.join(model_dir, "model.safetensors"), "wb") as f:
                f.write(b"\x00" * 1024)

            # Temporarily add tmpdir to search paths
            from sentinel_reverse.cli import DEFAULT_MODEL_SEARCH_PATHS
            original = DEFAULT_MODEL_SEARCH_PATHS.copy()
            DEFAULT_MODEL_SEARCH_PATHS.insert(0, tmpdir)
            try:
                models = discover_models()
                found = [m for m in models if m["name"] == "test-model-4bit"]
                assert len(found) == 1
                assert found[0]["type"] == "llama"
            finally:
                DEFAULT_MODEL_SEARCH_PATHS[:] = original


class TestCLIParser:
    """Test argument parser configuration."""

    def test_parser_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["test.bin"])
        assert args.target == "test.bin"
        assert args.mode == "standard"
        assert args.model is None
        assert args.resume is False
        assert args.verbose is False
        assert args.quiet is False

    def test_parser_exhaustive_mode(self):
        parser = build_parser()
        args = parser.parse_args(["test.bin", "-m", "exhaustive"])
        assert args.mode == "exhaustive"

    def test_parser_custom_params(self):
        parser = build_parser()
        args = parser.parse_args([
            "test.bin",
            "--confidence", "0.95",
            "--max-rounds", "20",
            "--max-functions", "100",
        ])
        assert args.confidence == 0.95
        assert args.max_rounds == 20
        assert args.max_functions == 100

    def test_parser_resume_flag(self):
        parser = build_parser()
        args = parser.parse_args(["test.bin", "--resume"])
        assert args.resume is True

    def test_parser_detect_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--detect", "test.bin"])
        assert args.detect is True

    def test_parser_list_models(self):
        parser = build_parser()
        args = parser.parse_args(["--list-models"])
        assert args.list_models is True
