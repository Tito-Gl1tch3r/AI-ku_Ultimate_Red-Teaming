import os

base = "/Users/naxoziwus/Desktop/Dragon-ThreatResearchHQ/Ransomware"

entries = {
    "INCRansom": {
        "report": "## INCRansom Report\nExtortion group that emerged in 2023. Exploits CVE-2023-46805 (Ivanti).",
        "mitre": "| Tactic | Technique ID | Technique Name | Behavior |\n|---|---|---|---|\n| Initial Access | T1190 | Exploit Public-Facing Application | Exploits CVE-2023-46805 |",
        "fingerprints": "title: INCRansom\nSPL: index=main INCRansom",
        "yara": "rule INCRansom_malware\n{\n    meta:\n        description = \"INCRansom\"\n        author = \"Dragon-ThreatResearchHQ\"\n        reference = \"http\"\n        threat_actor = \"INCRansom\"\n        malware_family = \"Ransomware\"\n        date = \"2023-01-01\"\n        hash = \"abcdef\"\n    strings:\n        $s1 = \"INCRansom\" ascii\n    condition:\n        uint16(0) == 0x5A4D and $s1\n}",
        "iocs": "type,value,description,threat_actor,campaign,confidence,source,tags\ncve,CVE-2023-46805,Ivanti exploit,INCRansom,camp1,high,osint,ransomware\nipv4,1.1.1.1,C2,INCRansom,camp1,high,osint,c2\ndomain,incrnsm.com,C2,INCRansom,camp1,high,osint,c2\nsha256,1111111111111111111111111111111111111111111111111111111111111111,payload,INCRansom,camp1,high,osint,payload\n"
    },
    "NightSpire": {
        "report": "## NightSpire Report\nA relatively new ransomware variant targeting Windows AD environments.",
        "mitre": "| Tactic | Technique ID | Technique Name | Behavior |\n|---|---|---|---|\n| Discovery | T1087 | Account Discovery | AD queries |",
        "fingerprints": "title: NightSpire\nSPL: index=main NightSpire",
        "yara": "rule NightSpire_malware\n{\n    meta:\n        description = \"NightSpire\"\n        author = \"Dragon-ThreatResearchHQ\"\n        reference = \"http\"\n        threat_actor = \"NightSpire\"\n        malware_family = \"Ransomware\"\n        date = \"2024-01-01\"\n        hash = \"abcdef\"\n    strings:\n        $s1 = \"NightSpire\" ascii\n    condition:\n        uint16(0) == 0x5A4D and $s1\n}",
        "iocs": "type,value,description,threat_actor,campaign,confidence,source,tags\nipv4,2.2.2.2,C2,NightSpire,camp1,high,osint,c2\ndomain,nightspire.com,C2,NightSpire,camp1,high,osint,c2\nsha256,2222222222222222222222222222222222222222222222222222222222222222,payload,NightSpire,camp1,high,osint,payload\nsha1,2222222222222222222222222222222222222222,payload,NightSpire,camp1,high,osint,payload\n"
    },
    "Nitrogen2.0": {
        "readme": "# Nitrogen2.0\n| Field | Value |\n|---|---|\n| Actor | Nitrogen2.0 |\n| Target | General |",
        "report": "## Nitrogen2.0 Report\nMalware campaign using malicious ads to deliver a Python-based initial access payload that often leads to ransomware.",
        "mitre": "| Tactic | Technique ID | Technique Name | Behavior |\n|---|---|---|---|\n| Initial Access | T1566 | Phishing | Malicious ads |",
        "fingerprints": "title: Nitrogen2.0\nSPL: index=main Nitrogen2.0",
        "yara": "rule Nitrogen2_malware\n{\n    meta:\n        description = \"Nitrogen2.0\"\n        author = \"Dragon-ThreatResearchHQ\"\n        reference = \"http\"\n        threat_actor = \"Nitrogen2.0\"\n        malware_family = \"Ransomware\"\n        date = \"2024-01-01\"\n        hash = \"abcdef\"\n    strings:\n        $s1 = \"Nitrogen2.0\" ascii\n    condition:\n        uint16(0) == 0x5A4D and $s1\n}",
        "iocs": "type,value,description,threat_actor,campaign,confidence,source,tags\nipv4,3.3.3.3,C2,Nitrogen2.0,camp1,high,osint,c2\ndomain,nitrogen.com,C2,Nitrogen2.0,camp1,high,osint,c2\nsha256,3333333333333333333333333333333333333333333333333333333333333333,payload,Nitrogen2.0,camp1,high,osint,payload\nsha1,3333333333333333333333333333333333333333,payload,Nitrogen2.0,camp1,high,osint,payload\n"
    },
    "Rhysida": {
        "report": "## Rhysida Report\nRansomware-as-a-service (RaaS). Targets education, healthcare, government. Drops via Cobalt Strike, uses AnyDesk.",
        "mitre": "| Tactic | Technique ID | Technique Name | Behavior |\n|---|---|---|---|\n| Command and Control | T1219 | Remote Access Software | AnyDesk |",
        "fingerprints": "title: Rhysida\nSPL: index=main Rhysida",
        "yara": "rule Rhysida_malware\n{\n    meta:\n        description = \"Rhysida\"\n        author = \"Dragon-ThreatResearchHQ\"\n        reference = \"http\"\n        threat_actor = \"Rhysida\"\n        malware_family = \"Ransomware\"\n        date = \"2023-01-01\"\n        hash = \"abcdef\"\n    strings:\n        $s1 = \"Rhysida\" ascii\n    condition:\n        uint16(0) == 0x5A4D and $s1\n}",
        "iocs": "type,value,description,threat_actor,campaign,confidence,source,tags\nipv4,4.4.4.4,C2,Rhysida,camp1,high,osint,c2\ndomain,rhysida.com,C2,Rhysida,camp1,high,osint,c2\nsha256,4444444444444444444444444444444444444444444444444444444444444444,payload,Rhysida,camp1,high,osint,payload\nsha1,4444444444444444444444444444444444444444,payload,Rhysida,camp1,high,osint,payload\n"
    }
}

for name, files in entries.items():
    d = os.path.join(base, name)
    os.makedirs(d, exist_ok=True)
    
    if "readme" in files:
        with open(os.path.join(d, "README.md"), "w") as f:
            f.write(files["readme"])
    
    with open(os.path.join(d, "report.md"), "w") as f:
        f.write(files["report"])
    
    with open(os.path.join(d, "mitre_attack.md"), "w") as f:
        f.write(files["mitre"])
        
    with open(os.path.join(d, "fingerprints.txt"), "w") as f:
        f.write(files["fingerprints"])
        
    with open(os.path.join(d, "iocs.csv"), "w") as f:
        f.write(files["iocs"])
        
    os.makedirs(os.path.join(d, "yara"), exist_ok=True)
    with open(os.path.join(d, "yara/rules.yar"), "w") as f:
        f.write(files["yara"])

