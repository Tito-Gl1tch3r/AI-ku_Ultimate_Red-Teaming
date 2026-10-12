import random
import uuid
import os
from datetime import datetime


def detect_behavior(cmdline):
    """
    Analyze command line for suspicious behavior.
    """
    cmd = cmdline.lower()

    if "powershell" in cmd:
        return "Suspicious PowerShell reverse shell detected"
    elif "psexec" in cmd:
        return "Potential lateral movement via PsExec"
    elif ("ping" in cmd or "curl" in cmd or "wget" in cmd) and ("&&" in cmd or ";" in cmd):
        return "Possible command injection attempt"
    elif "select" in cmd and "from" in cmd:
        return "Suspicious SQL query pattern (possible SQLi)"
    elif "<script>" in cmd or "javascript:" in cmd:
        return "XSS payload detected in user input"
    else:
        return "N/A"


def generate_sysmon_4688(process_name, parent_process, cmdline):
    """
    Generate a Sysmon-style process creation event (Event ID 4688).
    """
    detection_note = detect_behavior(cmdline)

    return {
        "event_id": 4688,
        "record_id": random.randint(1000, 9999),
        "time_generated": datetime.now().isoformat(),  # <-- ISO формат за plotly
        "process_guid": str(uuid.uuid4()),
        "parent_process": parent_process,
        "new_process": process_name,
        "command_line": cmdline,
        "integrity_level": "Medium",
        "detected": random.choice([True, False]),
        "detection_note": detection_note
    }


def generate_sysmon_log(event_dict, output_path="logs/sysmon_log.xml"):
    """
    Write event as Sysmon-compatible XML.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if not isinstance(event_dict, dict):
        raise ValueError("Event must be a dictionary.")

    xml_data = "\n        ".join(
        [f"<Data Name='{k}'>{v}</Data>" for k, v in event_dict.items()]
    )

    sysmon_template = f"""<Event>
    <System>
        <Provider Name="Microsoft-Windows-Sysmon"/>
        <EventID>1</EventID>
    </System>
    <EventData>
        {xml_data}
    </EventData>
</Event>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(sysmon_template)

    print("[+] Sysmon log written to:", output_path)
