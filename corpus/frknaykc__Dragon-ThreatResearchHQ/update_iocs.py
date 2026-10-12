import os

base = '/Users/naxoziwus/Desktop/Dragon-ThreatResearchHQ/Ransomware'

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)

# Update Cactus IOCs
path = os.path.join(base, 'Cactus')
write_file(f'{path}/iocs.csv', '''type,value,description,threat_actor,campaign,confidence,source,tags
ipv4,144.172.122.30,C2 Server,Cactus,2023,high,OSINT,c2
ipv4,45.61.147.176,C2 Server,Cactus,2023,high,OSINT,c2
url,http://zohoservice.net/anydesk.zip,Malicious download,Cactus,2023,high,OSINT,payload
url,http://216.107.136.46/Qliksens_update.zip,Malicious download,Cactus,2023,high,OSINT,payload
domain,qlik-sens-patch.zip,Malicious download,Cactus,2023,high,OSINT,payload
sha256,3ac8308a7378dfe047eacd393c861d32df34bb47535972eb0a35631ab964d14d,Cactus payload,Cactus,2023,high,OSINT,ransomware
sha256,6cb87cad36f56aefcefbe754605c00ac92e640857fd7ca5faab7b9542ef80c96,Cactus payload,Cactus,2023,high,OSINT,ransomware
''')

write_file(f'{path}/report.md', '''# Cactus Ransomware Technical Analysis
Cactus ransomware employs a combination of AES and RSA algorithms to encrypt business users' data, subsequently demanding a substantial ransom to restore access to the files. It primarily targets English-speaking users.

When preparing a file for encryption, Cactus changes the file extension to `.CTS0`. After encryption, the extension becomes `.CTS1`. Cactus also has a "quick mode" for encryption.

Cactus exploits known vulnerabilities in Fortinet VPN devices to gain initial access. The encryptor binary is distributed via a batch script extracting from 7-Zip. It uses `-s`, `-r`, and `-i` arguments for execution.
''')

write_file(f'{path}/mitre_attack.md', '''# MITRE ATT&CK
| Tactic | Technique ID | Technique Name | Behavior |
|--------|--------------|----------------|----------|
| Initial Access | T1133 | External Remote Services | Exploits Fortinet VPN devices |
| Execution | T1059.003 | Command and Scripting Interpreter: Windows Command Shell | Uses batch scripts to extract encryptor |
| Defense Evasion | T1140 | Deobfuscate/Decode Files or Information | Needs AES key provided via command line to decrypt itself |
| Impact | T1486 | Data Encrypted for Impact | Encrypts files with .CTS1 extension |
''')

# Update DragonForce IOCs
path = os.path.join(base, 'DragonForce')
write_file(f'{path}/iocs.csv', '''type,value,description,threat_actor,campaign,confidence,source,tags
ipv4,185.73.125.8,C2 Server,DragonForce,2023,high,OSINT,c2
ipv4,94.232.46.202,C2 Server,DragonForce,2023,high,OSINT,c2
ipv4,69.4.234.20,C2 Server,DragonForce,2023,high,OSINT,c2
ipv4,2.147.68.96,C2 Server,DragonForce,2023,high,OSINT,c2
ipv4,185.59.221.75,C2 Server,DragonForce,2023,high,OSINT,c2
md5,97B70E89B5313612A9E7A339EE82AB67,socks.exe,DragonForce,2023,high,OSINT,payload
md5,A50637F5F7A3E462135C0AE7C7AF0D91,a65.exe,DragonForce,2023,high,OSINT,payload
md5,BB7C575E798FF5243B5014777253635D,netscanold.exe,DragonForce,2023,high,OSINT,payload
md5,C111476F7B394776B515249ECB6B20E6,df.exe,DragonForce,2023,high,OSINT,payload
''')
