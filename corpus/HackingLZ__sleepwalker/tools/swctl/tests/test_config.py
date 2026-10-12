"""Verify the shared key config (config.json) plumbing.

Run: python3 -m swctl.tests.test_config   (from tools/).

Covers:
  * _cfg defaults match the built-in values in include/sw_core.h
  * an unmodified/empty config.json leaves every value at the defaults
  * custom values are picked up (and validated)
  * make_swconfig.py emits only the modified fields as #defines
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from swctl import _cfg
from swctl import core

FAILED = []


def check(label: str, cond: bool) -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        FAILED.append(label)


def _write_cfg(d: dict) -> Path:
    p = Path(tempfile.mkstemp(suffix=".json")[1])
    p.write_text(json.dumps(d))
    return p


def main() -> int:
    print("[defaults]")
    check("default aes_key", core.AES_KEY == _cfg.DEFAULT_AES_KEY)
    check("default config_nonce", core.CONFIG_NONCE == _cfg.DEFAULT_CONFIG_NONCE)
    check("default cron_xor_key", core.CRON_XOR_KEY == _cfg.DEFAULT_CRON_XOR_KEY)
    check("default sniff_xor_const", core.SNIFF_XOR_CONST == _cfg.DEFAULT_SNIFF_XOR_CONST)
    no_file = Path(tempfile.mkdtemp()) / "nope.json"
    old = os.environ.get("SW_CONFIG_FILE")
    os.environ["SW_CONFIG_FILE"] = str(no_file)
    try:
        check("missing file -> defaults", _cfg.load()["aes_key"] == _cfg.DEFAULT_AES_KEY)
        empty = _write_cfg({})
        os.environ["SW_CONFIG_FILE"] = str(empty)
        check("empty config -> defaults", _cfg.load()["aes_key"] == _cfg.DEFAULT_AES_KEY)
        blank = _write_cfg({"aes_key": "", "cron_xor_key": "  ",
                            "sniff_xor_const": ""})
        os.environ["SW_CONFIG_FILE"] = str(blank)
        check("blank fields -> defaults", _cfg.load()["sniff_xor_const"] == 0xAAAA)
    finally:
        if old is None:
            os.environ.pop("SW_CONFIG_FILE", None)
        else:
            os.environ["SW_CONFIG_FILE"] = old

    print("[custom values]")
    custom = _write_cfg({
        "aes_key": "00" * 32,
        "config_nonce": "ff" * 12,
        "cron_xor_key": "0102",
        "sniff_xor_const": "0xBEEF",
    })
    os.environ["SW_CONFIG_FILE"] = str(custom)
    try:
        c = _cfg.load()
        check("custom aes_key", c["aes_key"] == bytes(32))
        check("custom config_nonce", c["config_nonce"] == bytes([0xFF]) * 12)
        check("custom cron_xor_key", c["cron_xor_key"] == bytes.fromhex("0102"))
        check("custom sniff_xor_const", c["sniff_xor_const"] == 0xBEEF)
    finally:
        os.environ["SW_CONFIG_FILE"] = str(no_file)

    print("[validation]")
    for bad in ({"aes_key": "abc"}, {"aes_key": "ab" * 15},
                {"config_nonce": "ab"}, {"cron_xor_key": "" + "00" * 33},
                {"sniff_xor_const": "zzz"}, {"sniff_xor_const": 1 << 16}):
        p = _write_cfg(bad)
        os.environ["SW_CONFIG_FILE"] = str(p)
        try:
            _cfg.load()
            check(f"rejects {bad}", False)
        except SystemExit:
            check(f"rejects {bad}", True)
    os.environ["SW_CONFIG_FILE"] = str(no_file)

    print("[make_swconfig.py]")
    gen = Path(__file__).resolve().parents[3] / "build" / "make_swconfig.py"

    def _gen(cfg: dict) -> str:
        p = _write_cfg(cfg)
        r = subprocess.run(
            [sys.executable, str(gen), str(p)],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"make_swconfig failed: {r.stderr}")
        return r.stdout

    out = _gen({})
    check("stock config -> no defines",
          "#define SW_AES_KEY" not in out
          and "#define SW_SNIFF_XOR_CONST" not in out)
    out = _gen({"aes_key": "11" * 32, "sniff_xor_const": 43690})
    check("only modified fields emitted",
          "#define SW_AES_KEY" in out
          and "0x11,0x11" in out
          and "#define SW_SNIFF_XOR_CONST 43690u" in out
          and "#define SW_CONFIG_NONCE" not in out
          and "#define SW_CRON_XOR_KEY" not in out)
    out = _gen({"cron_xor_key": "90FDFD02"})
    check("cron key normalize+emit",
          "#define SW_CRON_XOR_KEY" in out
          and "0x90,0xFD,0xFD,0x02" in out
          and "#define SW_CRON_XOR_KEY_LEN 4" in out)
    out = _gen({"cron_xor_key": "abcd"})
    check("short cron key padded to 32",
          "0xAB,0xCD,0x00,0x00" in out
          and "#define SW_CRON_XOR_KEY_LEN 2" in out)

    print()
    if FAILED:
        print(f"FAILURES: {len(FAILED)}")
        return 1
    print("ALL CONFIG TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
