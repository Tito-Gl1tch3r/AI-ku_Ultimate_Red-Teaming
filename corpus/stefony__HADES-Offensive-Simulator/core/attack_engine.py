from time import sleep
from colorama import Fore
from datetime import datetime
import uuid

from core.sysmon_simulator import generate_sysmon_4688


def now():
    """Standard ISO timestamp for consistency across all events."""
    return datetime.now().isoformat()


def wrap_sysmon_event(event, detected=True):
    """Add additional metadata to sysmon events"""
    event["time_generated"] = now()
    event["detected"] = detected
    return event


def simulate_credential_dump():
    print(Fore.RED + "[*] Simulating credential dumping using mimikatz...")
    sleep(1)
    print(Fore.YELLOW + "sekurlsa::logonpasswords")
    sleep(1)
    print(Fore.GREEN + "[+] Dump complete.")

    return {
        "attack": "Credential Dump",
        "tool": "Mimikatz",
        "technique": "T1003.001",
        "timestamp": now(),
        "event_id": str(uuid.uuid4())
    }


def simulate_reverse_shell():
    print(Fore.RED + "[*] Simulating reverse shell...")
    sleep(1)

    attacker_ip = "192.168.1.66"
    attacker_port = 4444
    payload = "cG93ZXJzaGVsbC5leGUgLW5vcGAgLUNvbW1hbmQgJ2Jhc2gtaSA+ICRudWxsID4gJjEn"
    decoded_cmd = "powershell.exe -nop -Command 'bash -i > $null 2>&1'"

    print(Fore.YELLOW + f"Encoded payload: {payload}")
    sleep(1)

    sysmon_event = generate_sysmon_4688("powershell.exe", "explorer.exe", decoded_cmd)
    sysmon_event = wrap_sysmon_event(sysmon_event)

    print(Fore.GREEN + "[+] Reverse shell launched (simulated).")

    return {
        "attack": "Reverse Shell",
        "technique": "T1059.001",
        "obfuscation": "base64 encoded payload",
        "payload": payload,
        "source_ip": attacker_ip,
        "dest_port": attacker_port,
        "stealth_score": 7.5,
        "timestamp": now(),
        "event_id": str(uuid.uuid4()),
        "sysmon": sysmon_event
    }


def simulate_command_injection():
    print(Fore.RED + "[*] Simulating Command Injection...")
    sleep(1)

    cmd_line = "ping 127.0.0.1 && whoami"
    sysmon_event = generate_sysmon_4688("cmd.exe", "webserver.exe", cmd_line)
    sysmon_event = wrap_sysmon_event(sysmon_event)

    print(Fore.GREEN + "[+] Command Injection executed (simulated).")

    return {
        "attack": "Command Injection",
        "technique": "T1059",
        "vulnerability": "Unsanitized user input in OS command",
        "endpoint": "/status?host=127.0.0.1 && whoami",
        "timestamp": now(),
        "event_id": str(uuid.uuid4()),
        "sysmon": sysmon_event
    }


def simulate_sql_injection():
    print(Fore.RED + "[*] Simulating SQL Injection...")
    sleep(1)

    payload = "' OR '1'='1';--"
    cmd_line = f"SELECT * FROM users WHERE username = '{payload}'"
    sysmon_event = generate_sysmon_4688("sqlservr.exe", "webapp.exe", cmd_line)
    sysmon_event = wrap_sysmon_event(sysmon_event)

    print(Fore.GREEN + "[+] SQLi simulated.")

    return {
        "attack": "SQL Injection",
        "technique": "T1505.001",
        "payload": payload,
        "affected_endpoint": "/login",
        "database": "MSSQL",
        "timestamp": now(),
        "event_id": str(uuid.uuid4()),
        "sysmon": sysmon_event
    }


def simulate_xss():
    print(Fore.RED + "[*] Simulating Reflected XSS...")
    sleep(1)

    payload = "<script>alert('Hacked');</script>"
    print(Fore.YELLOW + f"Injected XSS payload: {payload}")
    sleep(1)

    return {
        "attack": "Reflected XSS",
        "technique": "T1059.007",
        "payload": payload,
        "target_page": "/search?q=<script>alert('Hacked');</script>",
        "timestamp": now(),
        "event_id": str(uuid.uuid4())
    }


def simulate_lateral_movement():
    print(Fore.RED + "[*] Simulating Lateral Movement via PsExec...")
    sleep(1)

    cmd_line = "PsExec.exe \\\\10.0.0.5 -u admin -p password cmd.exe"
    sysmon_event = generate_sysmon_4688("PsExec.exe", "cmd.exe", cmd_line)
    sysmon_event = wrap_sysmon_event(sysmon_event)

    print(Fore.GREEN + "[+] Lateral movement simulated.")

    return {
        "attack": "Lateral Movement",
        "technique": "T1021.002",
        "tool": "PsExec",
        "target_host": "10.0.0.5",
        "timestamp": now(),
        "event_id": str(uuid.uuid4()),
        "sysmon": sysmon_event
    }
def simulate_insecure_deserialization():
    return {
        "attack": "Insecure Deserialization",
        "description": "Simulates exploitation of insecure object deserialization.",
        "mitre_id": "T1536"
    }

def simulate_phishing():
    return {
        "attack": "Phishing (Credential Harvesting)",
        "description": "Simulates a phishing page to collect user credentials.",
        "mitre_id": "T1566.001"
    }
