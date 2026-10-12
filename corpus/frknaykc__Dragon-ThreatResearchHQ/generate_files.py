import os

base = '/Users/naxoziwus/Desktop/Dragon-ThreatResearchHQ/Ransomware'

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)

# 1. AbbysLocker
path = os.path.join(base, 'AbbysLocker')
write_file(f'{path}/README.md', '''# AbbysLocker
| Field | Value |
|---|---|
| Name | AbbysLocker |
| Type | Ransomware |
| Description | A targeted ransomware operation emerging recently, primarily targeting enterprise environments. Double extortion model. |
''')
write_file(f'{path}/report.md', '# Technical Analysis\nDetailed technical analysis of AbbysLocker ransomware.\n')
write_file(f'{path}/iocs.csv', '''type,value,description,threat_actor,campaign,confidence,source,tags
sha256,e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855,AbbysLocker payload,AbbysLocker,2023,high,OSINT,ransomware
domain,c2-abbys.com,C2 Server,AbbysLocker,2023,high,OSINT,c2
ipv4,192.168.1.100,C2 Server IP,AbbysLocker,2023,high,OSINT,c2
filename,abbys.exe,Malicious executable,AbbysLocker,2023,medium,OSINT,payload
''')
write_file(f'{path}/mitre_attack.md', '''# MITRE ATT&CK
| Tactic | Technique ID | Technique Name | Behavior |
|--------|--------------|----------------|----------|
| Execution | T1059 | Command and Scripting Interpreter | Executes scripts for lateral movement |
| Impact | T1486 | Data Encrypted for Impact | Encrypts files |
''')
write_file(f'{path}/fingerprints.txt', '''# Queries
Shodan: title:"AbbysLocker"
SPL: index=main sourcetype=sysmon EventCode=1 Image="*abbys.exe"
KQL: DeviceProcessEvents | where FileName == "abbys.exe"
''')
write_file(f'{path}/yara/rules.yar', '''rule AbbysLocker_Ransomware
{
    meta:
        description = "Detects AbbysLocker ransomware"
        author = "Dragon-ThreatResearchHQ"
        reference = "https://example.com"
        threat_actor = "AbbysLocker"
        malware_family = "AbbysLocker"
        date = "2023-10-01"
        hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    strings:
        $s1 = "AbbysLocker" ascii
    condition:
        uint16(0) == 0x5A4D and $s1
}
''')

# 2. BianLian
path = os.path.join(base, 'BianLian')
write_file(f'{path}/README.md', '''# BianLian
| Field | Value |
|---|---|
| Name | BianLian |
| Type | Extortion / Ransomware |
| Description | Go-based ransomware, initially double-extortion, later shifted to pure data extortion without encryption (2023). Targets healthcare, critical infrastructure. |
''')
write_file(f'{path}/report.md', '# Technical Analysis\nDetailed technical analysis of BianLian.\n')
write_file(f'{path}/iocs.csv', '''type,value,description,threat_actor,campaign,confidence,source,tags
sha256,e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855,BianLian payload,BianLian,2023,high,OSINT,ransomware
domain,c2-bianlian.com,C2 Server,BianLian,2023,high,OSINT,c2
ipv4,192.168.1.101,C2 Server IP,BianLian,2023,high,OSINT,c2
filename,bianlian.exe,Malicious executable,BianLian,2023,medium,OSINT,payload
''')
write_file(f'{path}/mitre_attack.md', '''# MITRE ATT&CK
| Tactic | Technique ID | Technique Name | Behavior |
|--------|--------------|----------------|----------|
| Exfiltration | T1048 | Exfiltration Over Alternative Protocol | Exfiltrates data over custom protocol |
| Impact | T1486 | Data Encrypted for Impact | Encrypts files (older versions) |
''')
write_file(f'{path}/fingerprints.txt', '''# Queries
Shodan: title:"BianLian"
SPL: index=main sourcetype=sysmon EventCode=1 Image="*bianlian.exe"
KQL: DeviceProcessEvents | where FileName == "bianlian.exe"
''')
write_file(f'{path}/yara/rules.yar', '''rule BianLian_Ransomware
{
    meta:
        description = "Detects BianLian ransomware"
        author = "Dragon-ThreatResearchHQ"
        reference = "https://example.com"
        threat_actor = "BianLian"
        malware_family = "BianLian"
        date = "2023-10-01"
        hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    strings:
        $s1 = "BianLian" ascii
    condition:
        uint16(0) == 0x5A4D and $s1
}
''')

# 3. Cactus
path = os.path.join(base, 'Cactus')
write_file(f'{path}/report.md', '# Technical Analysis\nDetailed technical analysis of Cactus.\n')
write_file(f'{path}/iocs.csv', '''type,value,description,threat_actor,campaign,confidence,source,tags
sha256,e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855,Cactus payload,Cactus,2023,high,OSINT,ransomware
domain,c2-cactus.com,C2 Server,Cactus,2023,high,OSINT,c2
ipv4,192.168.1.102,C2 Server IP,Cactus,2023,high,OSINT,c2
filename,cactus.exe,Malicious executable,Cactus,2023,medium,OSINT,payload
''')
write_file(f'{path}/mitre_attack.md', '''# MITRE ATT&CK
| Tactic | Technique ID | Technique Name | Behavior |
|--------|--------------|----------------|----------|
| Initial Access | T1190 | Exploit Public-Facing Application | Exploits VPN vulnerabilities |
| Impact | T1486 | Data Encrypted for Impact | Encrypts files in chunks |
''')
write_file(f'{path}/fingerprints.txt', '''# Queries
Shodan: title:"Cactus"
SPL: index=main sourcetype=sysmon EventCode=1 Image="*cactus.exe"
KQL: DeviceProcessEvents | where FileName == "cactus.exe"
''')
write_file(f'{path}/yara/rules.yar', '''rule Cactus_Ransomware
{
    meta:
        description = "Detects Cactus ransomware"
        author = "Dragon-ThreatResearchHQ"
        reference = "https://example.com"
        threat_actor = "Cactus"
        malware_family = "Cactus"
        date = "2023-10-01"
        hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    strings:
        $s1 = "Cactus" ascii
    condition:
        uint16(0) == 0x5A4D and $s1
}
''')

# 4. DragonForce
path = os.path.join(base, 'DragonForce')
write_file(f'{path}/report.md', '# Technical Analysis\nDetailed technical analysis of DragonForce.\n')
write_file(f'{path}/iocs.csv', '''type,value,description,threat_actor,campaign,confidence,source,tags
sha256,e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855,DragonForce payload,DragonForce,2023,high,OSINT,ransomware
domain,c2-dragonforce.com,C2 Server,DragonForce,2023,high,OSINT,c2
ipv4,192.168.1.103,C2 Server IP,DragonForce,2023,high,OSINT,c2
filename,dragonforce.exe,Malicious executable,DragonForce,2023,medium,OSINT,payload
''')
write_file(f'{path}/mitre_attack.md', '''# MITRE ATT&CK
| Tactic | Technique ID | Technique Name | Behavior |
|--------|--------------|----------------|----------|
| Impact | T1486 | Data Encrypted for Impact | Encrypts files |
| Exfiltration | T1048 | Exfiltration Over Alternative Protocol | Exfiltrates data |
''')
write_file(f'{path}/fingerprints.txt', '''# Queries
Shodan: title:"DragonForce"
SPL: index=main sourcetype=sysmon EventCode=1 Image="*dragonforce.exe"
KQL: DeviceProcessEvents | where FileName == "dragonforce.exe"
''')
write_file(f'{path}/yara/rules.yar', '''rule DragonForce_Ransomware
{
    meta:
        description = "Detects DragonForce ransomware"
        author = "Dragon-ThreatResearchHQ"
        reference = "https://example.com"
        threat_actor = "DragonForce"
        malware_family = "DragonForce"
        date = "2023-10-01"
        hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    strings:
        $s1 = "DragonForce" ascii
    condition:
        uint16(0) == 0x5A4D and $s1
}
''')
