"""Verify the controller against the SLEEPWALKER write-up vectors.

Run: python3 -m swctl.tests.test_vectors   (from tools/).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from swctl import framing
from swctl.bytecode import compile_program, decode_program, render_tree
from swctl.core import (
    MAGIC_MIN_BLOCK,
    SNIFF_MIN_PACKET,
    SNIFF_XOR_CONST,
    base32_decode,
    base32_encode,
    ccm_open,
    crc32,
    crc8,
)

FAILED = []


def check(label: str, cond: bool) -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    if not cond:
        FAILED.append(label)


def rd16(b: bytes, off: int) -> int:
    return int.from_bytes(b[off:off + 2], "big")


def rd32(b: bytes, off: int) -> int:
    return int.from_bytes(b[off:off + 4], "big")


def magic_check(pkt: bytes) -> bool:
    """Re-implement the six gates the implant uses to accept a packet."""
    P = len(pkt)
    if P < SNIFF_MIN_PACKET:
        return False
    w1 = rd16(pkt, P - 4)
    w2 = rd16(pkt, P - 2)
    B = ((w1 ^ w2) ^ SNIFF_XOR_CONST) & 0xFFFF
    if B < MAGIC_MIN_BLOCK or B > 2048 or B > P:
        return False
    if rd16(pkt, P - B) != (w1 + w2) & 0xFFFF:
        return False
    env_len = B - 10
    if env_len < 28:
        return False
    crc = crc32(pkt[P - B:P - 8], 0)
    crc = crc32(pkt[P - 4:P], crc)
    if rd32(pkt, P - 8) != crc:
        return False
    env = pkt[P - B + 2:P - B + 2 + env_len]
    nonce, tag, ct = env[:12], env[12:28], env[28:]
    try:
        ccm_open(nonce, ct, tag)
    except ValueError:
        return False
    return True


def main() -> int:
    print("[DNS vector]")
    mid = "qfoceywmw4etcjdp2nptiti"
    check("base32 middle == blog string",
          base32_encode(bytes.fromhex("815c2262ccb70931246fd35f344d")) == mid)
    check("crc8(middle) == 0x65", crc8(mid.encode()) == 0x65)
    # Standard CCM reproduces the published DNS envelope.
    nonce = bytes.fromhex("815c2262ccb709")
    ct, tag = __import__("swctl.core", fromlist=["ccm_seal"]).ccm_seal(
        nonce, bytes.fromhex("0c003c"), 4)
    check("ct == 5f344d", ct == bytes.fromhex("5f344d"))
    check("tag == 31246fd3", tag == bytes.fromhex("31246fd3"))
    check("ccm open roundtrip",
          ccm_open(nonce, ct, tag) == bytes.fromhex("0c003c"))

    print("[DSL compile]")
    check("SLEEP_SECONDS 60 -> 0c003c",
          compile_program("SLEEP_SECONDS 60") == bytes.fromhex("0c003c"))
    check("SNIFF_MAGIC * 0 -> 87012a0000",
          compile_program("SNIFF_MAGIC * 0") == bytes.fromhex("87012a0000"))
    check("EXIT -> 06", compile_program("EXIT") == bytes.fromhex("06"))
    # Blog's full CRON_SCHEDULE example (nested program is XOR-masked).
    cron = compile_program(
        "CRON_SCHEDULE 0x1 0x200 0xFFFFFFFE 0x3E { SLEEP_RANDOM 60 }")
    check("CRON_SCHEDULE == blog bytes",
          cron == bytes.fromhex(
              "0e000000000000000100000200fffffffe3e039dfdc1"))

    print("[Magic packet]")
    boot = bytes.fromhex("87012a0000")
    mp = framing.build_magic_packet(boot)
    check("packet is 48 bytes", len(mp) == SNIFF_MIN_PACKET)
    check("passes all six gates", magic_check(mp))
    # tamper -> rejected
    bad = bytearray(mp)
    bad[7] ^= 0x01
    check("tampered envelope rejected", not magic_check(bytes(bad)))

    print("[Decode tree]")
    tree = render_tree(decode_program(boot))
    check("decode SNIFF_MAGIC tree", "SNIFF_MAGIC" in tree and "*" in tree)

    print()
    if FAILED:
        print(f"FAILURES: {len(FAILED)}")
        return 1
    print("ALL CONTROLLER TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
