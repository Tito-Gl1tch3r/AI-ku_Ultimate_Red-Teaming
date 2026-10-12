"""Run a DSL task against the PROD build (no debug log) and verify via the
mac-side UDP marker collector (port 9100). Usage:
  python3 -m function_test.prod_run <dsl> <marker-hex> [--no-restart]
"""
import sys, time, subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HOST = "192.168.1.100"
UDPLOG = "/tmp/udp_collector.log"

def _ssh(cmd):
    r = subprocess.run(["sshpass","-p","ChangeMe123!","ssh","-o","StrictHostKeyChecking=no",
                        f"operator@{HOST}", cmd], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    return "\n".join(l for l in r.stdout.splitlines()
                     if not l.startswith(("WARNING","**","Host key","|","+--","CONNECTED","The authenticity"))).strip()

def udp_log_lines():
    try:
        return open(UDPLOG).read().splitlines()
    except FileNotFoundError:
        return []

def main(argv):
    dsl = argv[0]
    marker = argv[1].lower() if len(argv) > 1 else ""
    text = Path(dsl).read_text()
    before = set(udp_log_lines())
    # send via magic-over-UDP (imports framing)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from send import send_magic_udp, restart, HOST as H
    if "--no-restart" not in argv:
        restart()
        time.sleep(2)
    prog = send_magic_udp(text, 9999)
    print(f"sent {len(prog)}-byte task")
    time.sleep(3)
    after = set(udp_log_lines()) - before
    print("--- new UDP marker lines ---")
    for l in sorted(after):
        print(" ", l)
    if marker:
        found = [l for l in after if marker in l]
        print("MARKER_MATCH" if found else "MARKER_MISS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
