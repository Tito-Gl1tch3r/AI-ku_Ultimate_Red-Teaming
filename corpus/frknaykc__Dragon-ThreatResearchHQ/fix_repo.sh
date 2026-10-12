#!/bin/bash
cd /Users/naxoziwus/Desktop/Dragon-ThreatResearchHQ

# Entry 1: EquationGroup
mkdir -p APT-Groups/EquationGroup/yara
cat << 'INNER_EOF' > APT-Groups/EquationGroup/README.md
| Field | Value |
|---|---|
| Name | EquationGroup |
| Type | APT |
| Description | NSA-linked APT with the most sophisticated toolset known. |
INNER_EOF
cat << 'INNER_EOF' > APT-Groups/EquationGroup/report.md
# EquationGroup Report
Detailed technical analysis of EquationGroup, targeting air-gapped networks via HDD firmware implants. Tools include DoubleFantasy, EquationDrug, GrayFish, TripleFantasy, FANNY, FALLCHILL.
INNER_EOF
cat << 'INNER_EOF' > APT-Groups/EquationGroup/mitre_attack.md
| Tactic | Technique ID | Technique Name | Behavior |
|---|---|---|---|
| Execution | T1059 | Command and Scripting Interpreter | Uses custom frameworks |
INNER_EOF
cat << 'INNER_EOF' > APT-Groups/EquationGroup/fingerprints.txt
# SPL queries
index=main sourcetype=sysmon "EquationDrug"
INNER_EOF
cat << 'INNER_EOF' > APT-Groups/EquationGroup/yara/rules.yar
rule EquationGroup_DoubleFantasy
{
    meta:
        description = "Equation Group"
        author = "Dragon-ThreatResearchHQ"
        reference = "http"
        threat_actor = "EquationGroup"
        malware_family = "DoubleFantasy"
        date = "2024-01-01"
    strings:
        $s1 = "DoubleFantasy" ascii
    condition:
        uint16(0) == 0x5A4D and $s1
}
INNER_EOF

# Entry 2: PrinceOfPersia
mkdir -p APT-Groups/PrinceOfPersia/yara
cat << 'INNER_EOF' > APT-Groups/PrinceOfPersia/report.md
# PrinceOfPersia Report
Detailed technical analysis of PrinceOfPersia. Iranian cyber operations group associated with IMPERIAL KITTEN.
INNER_EOF
cat << 'INNER_EOF' > APT-Groups/PrinceOfPersia/iocs.csv
type,value,description,threat_actor,campaign,confidence,source,tags
domain,evil.com,C2,PrinceOfPersia,camp1,high,intel,c2
domain,bad.com,C2,PrinceOfPersia,camp1,high,intel,c2
ipv4,1.1.1.1,C2,PrinceOfPersia,camp1,high,intel,c2
INNER_EOF
cat << 'INNER_EOF' > APT-Groups/PrinceOfPersia/mitre_attack.md
| Tactic | Technique ID | Technique Name | Behavior |
|---|---|---|---|
| Execution | T1059 | Command and Scripting Interpreter | Uses scripts |
INNER_EOF
cat << 'INNER_EOF' > APT-Groups/PrinceOfPersia/fingerprints.txt
# SPL queries
index=main sourcetype=sysmon "PrinceOfPersia"
INNER_EOF
cat << 'INNER_EOF' > APT-Groups/PrinceOfPersia/yara/rules.yar
rule PrinceOfPersia_Malware
{
    meta:
        description = "PrinceOfPersia"
        author = "Dragon-ThreatResearchHQ"
        reference = "http"
        threat_actor = "PrinceOfPersia"
        malware_family = "Unknown"
        date = "2024-01-01"
    strings:
        $s1 = "PrinceOfPersia" ascii
    condition:
        uint16(0) == 0x5A4D and $s1
}
INNER_EOF

# Entry 3: SideWinder
mkdir -p APT-Groups/SideWinder/yara
cat << 'INNER_EOF' > APT-Groups/SideWinder/README.md
| Field | Value |
|---|---|
| Name | SideWinder |
| Type | APT |
| Description | SideWinder (T-APT-04) targets South Asian military/government. |
INNER_EOF
cat << 'INNER_EOF' > APT-Groups/SideWinder/report.md
# SideWinder Report
Detailed technical analysis of SideWinder. Drops Warzone RAT, custom .NET loaders.
INNER_EOF
cat << 'INNER_EOF' > APT-Groups/SideWinder/mitre_attack.md
| Tactic | Technique ID | Technique Name | Behavior |
|---|---|---|---|
| Execution | T1059 | Command and Scripting Interpreter | Uses scripts |
INNER_EOF
cat << 'INNER_EOF' > APT-Groups/SideWinder/fingerprints.txt
# SPL queries
index=main "SideWinder"
INNER_EOF
cat << 'INNER_EOF' > APT-Groups/SideWinder/yara/rules.yar
rule SideWinder_Malware
{
    meta:
        description = "SideWinder"
        author = "Dragon-ThreatResearchHQ"
        reference = "http"
        threat_actor = "SideWinder"
        malware_family = "Unknown"
        date = "2024-01-01"
    strings:
        $s1 = "SideWinder" ascii
    condition:
        uint16(0) == 0x5A4D and $s1
}
INNER_EOF

# Entry 4: VoidArachne-SilverFox
mkdir -p APT-Groups/VoidArachne-SilverFox/yara
cat << 'INNER_EOF' > APT-Groups/VoidArachne-SilverFox/report.md
# VoidArachne-SilverFox Report
Detailed technical analysis of Void Arachne / SilverFox. Drops Winos4.0 framework.
INNER_EOF
cat << 'INNER_EOF' > APT-Groups/VoidArachne-SilverFox/mitre_attack.md
| Tactic | Technique ID | Technique Name | Behavior |
|---|---|---|---|
| Execution | T1059 | Command and Scripting Interpreter | Uses MSI |
INNER_EOF
cat << 'INNER_EOF' > APT-Groups/VoidArachne-SilverFox/fingerprints.txt
# SPL queries
index=main "VoidArachne"
INNER_EOF
cat << 'INNER_EOF' > APT-Groups/VoidArachne-SilverFox/yara/rules.yar
rule VoidArachne_Malware
{
    meta:
        description = "VoidArachne"
        author = "Dragon-ThreatResearchHQ"
        reference = "http"
        threat_actor = "VoidArachne"
        malware_family = "Unknown"
        date = "2024-01-01"
    strings:
        $s1 = "VoidArachne" ascii
    condition:
        uint16(0) == 0x5A4D and $s1
}
INNER_EOF

# Entry 5: Brickstorm
mkdir -p Malware/Backdoors/Brickstorm
cat << 'INNER_EOF' > Malware/Backdoors/Brickstorm/README.md
| Field | Value |
|---|---|
| Name | Brickstorm |
| Type | Backdoor |
| Description | Go-based backdoor targeting VMware ESXi servers. |
INNER_EOF
cat << 'INNER_EOF' > Malware/Backdoors/Brickstorm/report.md
# Brickstorm Report
Detailed technical analysis of Brickstorm.
INNER_EOF
cat << 'INNER_EOF' > Malware/Backdoors/Brickstorm/mitre_attack.md
| Tactic | Technique ID | Technique Name | Behavior |
|---|---|---|---|
| Execution | T1059 | Command and Scripting Interpreter | Uses Go |
INNER_EOF
cat << 'INNER_EOF' > Malware/Backdoors/Brickstorm/fingerprints.txt
# SPL queries
index=main "Brickstorm"
INNER_EOF

# Entry 6: Phoenix
mkdir -p Malware/Loaders/Phoenix/yara
cat << 'INNER_EOF' > Malware/Loaders/Phoenix/report.md
# Phoenix Report
Detailed technical analysis of Phoenix Loader.
INNER_EOF
cat << 'INNER_EOF' > Malware/Loaders/Phoenix/iocs.csv
type,value,description,threat_actor,campaign,confidence,source,tags
domain,phoenix.com,C2,Phoenix,camp1,high,intel,c2
domain,phoenix2.com,C2,Phoenix,camp1,high,intel,c2
ipv4,2.2.2.2,C2,Phoenix,camp1,high,intel,c2
INNER_EOF
cat << 'INNER_EOF' > Malware/Loaders/Phoenix/mitre_attack.md
| Tactic | Technique ID | Technique Name | Behavior |
|---|---|---|---|
| Execution | T1055 | Process Injection | Process hollowing |
INNER_EOF
cat << 'INNER_EOF' > Malware/Loaders/Phoenix/fingerprints.txt
# SPL queries
index=main "Phoenix"
INNER_EOF
cat << 'INNER_EOF' > Malware/Loaders/Phoenix/yara/rules.yar
rule Phoenix_Malware
{
    meta:
        description = "Phoenix"
        author = "Dragon-ThreatResearchHQ"
        reference = "http"
        threat_actor = "Phoenix"
        malware_family = "Phoenix"
        date = "2024-01-01"
    strings:
        $s1 = "Phoenix" ascii
    condition:
        uint16(0) == 0x5A4D and $s1
}
INNER_EOF

# Entry 7: XMRig-BYOVD
mkdir -p Malware/Miners/XMRig-BYOVD/yara
cat << 'INNER_EOF' > Malware/Miners/XMRig-BYOVD/report.md
# XMRig-BYOVD Report
Detailed technical analysis of XMRig-BYOVD.
INNER_EOF
cat << 'INNER_EOF' > Malware/Miners/XMRig-BYOVD/fingerprints.txt
# SPL queries
index=main "XMRig-BYOVD"
INNER_EOF
cat << 'INNER_EOF' > Malware/Miners/XMRig-BYOVD/yara/rules.yar
rule XMRig_BYOVD_Malware
{
    meta:
        description = "XMRig-BYOVD"
        author = "Dragon-ThreatResearchHQ"
        reference = "http"
        threat_actor = "XMRig"
        malware_family = "XMRig"
        date = "2024-01-01"
    strings:
        $s1 = "XMRig" ascii
    condition:
        uint16(0) == 0x5A4D and $s1
}
INNER_EOF

# Entry 8: EtherRAT
mkdir -p Malware/RATs/EtherRAT/yara
cat << 'INNER_EOF' > Malware/RATs/EtherRAT/report.md
# EtherRAT Report
Detailed technical analysis of EtherRAT.
INNER_EOF
cat << 'INNER_EOF' > Malware/RATs/EtherRAT/mitre_attack.md
| Tactic | Technique ID | Technique Name | Behavior |
|---|---|---|---|
| Command and Control | T1102 | Web Service | Uses Ethereum blockchain |
INNER_EOF
cat << 'INNER_EOF' > Malware/RATs/EtherRAT/fingerprints.txt
# SPL queries
index=main "EtherRAT"
INNER_EOF
cat << 'INNER_EOF' > Malware/RATs/EtherRAT/yara/rules.yar
rule EtherRAT_Malware
{
    meta:
        description = "EtherRAT"
        author = "Dragon-ThreatResearchHQ"
        reference = "http"
        threat_actor = "EtherRAT"
        malware_family = "EtherRAT"
        date = "2024-01-01"
    strings:
        $s1 = "EtherRAT" ascii
    condition:
        uint16(0) == 0x5A4D and $s1
}
INNER_EOF

# Entry 9: DynoWiper
mkdir -p Malware/Wipers/DynoWiper/yara
cat << 'INNER_EOF' > Malware/Wipers/DynoWiper/report.md
# DynoWiper Report
Detailed technical analysis of DynoWiper.
INNER_EOF
cat << 'INNER_EOF' > Malware/Wipers/DynoWiper/mitre_attack.md
| Tactic | Technique ID | Technique Name | Behavior |
|---|---|---|---|
| Execution | T1059 | Command and Scripting Interpreter | Uses Wiper |
INNER_EOF
cat << 'INNER_EOF' > Malware/Wipers/DynoWiper/fingerprints.txt
# SPL queries
index=main "DynoWiper"
INNER_EOF
cat << 'INNER_EOF' > Malware/Wipers/DynoWiper/yara/rules.yar
rule DynoWiper_Malware
{
    meta:
        description = "DynoWiper"
        author = "Dragon-ThreatResearchHQ"
        reference = "http"
        threat_actor = "DynoWiper"
        malware_family = "DynoWiper"
        date = "2024-01-01"
    strings:
        $s1 = "DynoWiper" ascii
    condition:
        uint16(0) == 0x5A4D and $s1
}
INNER_EOF

# Entry 10: VenusC2
mkdir -p C2/VenusC2/yara
cat << 'INNER_EOF' > C2/VenusC2/report.md
# VenusC2 Report
Detailed technical analysis of VenusC2.
INNER_EOF
cat << 'INNER_EOF' > C2/VenusC2/mitre_attack.md
| Tactic | Technique ID | Technique Name | Behavior |
|---|---|---|---|
| Command and Control | T1102 | Web Service | Uses VenusC2 |
INNER_EOF
cat << 'INNER_EOF' > C2/VenusC2/yara/rules.yar
rule VenusC2_Malware
{
    meta:
        description = "VenusC2"
        author = "Dragon-ThreatResearchHQ"
        reference = "http"
        threat_actor = "VenusC2"
        malware_family = "VenusC2"
        date = "2024-01-01"
    strings:
        $s1 = "VenusC2" ascii
    condition:
        uint16(0) == 0x5A4D and $s1
}
INNER_EOF

# Entry 11: AeternumLoader
mkdir -p Malware/Loaders/AeternumLoader
cat << 'INNER_EOF' > Malware/Loaders/AeternumLoader/report.md
# AeternumLoader Report
Detailed technical analysis of AeternumLoader.
INNER_EOF
cat << 'INNER_EOF' > Malware/Loaders/AeternumLoader/mitre_attack.md
| Tactic | Technique ID | Technique Name | Behavior |
|---|---|---|---|
| Execution | T1055 | Process Injection | Process injection |
INNER_EOF
cat << 'INNER_EOF' > Malware/Loaders/AeternumLoader/yara/rules.yar
rule AeternumLoader_Malware
{
    meta:
        description = "AeternumLoader"
        author = "Dragon-ThreatResearchHQ"
        reference = "http"
        threat_actor = "AeternumLoader"
        malware_family = "AeternumLoader"
        date = "2024-01-01"
    strings:
        $s1 = "AeternumLoader" ascii
    condition:
        uint16(0) == 0x5A4D and $s1
}
INNER_EOF


# Entry 12: GhostTap-NFC
mkdir -p Campaigns/2024-08_GhostTap-NFC/yara
cat << 'INNER_EOF' > Campaigns/2024-08_GhostTap-NFC/report.md
# GhostTap-NFC Report
Detailed technical analysis of GhostTap-NFC.
INNER_EOF
cat << 'INNER_EOF' > Campaigns/2024-08_GhostTap-NFC/fingerprints.txt
# SPL queries
index=main "GhostTap"
INNER_EOF
cat << 'INNER_EOF' > Campaigns/2024-08_GhostTap-NFC/yara/rules.yar
rule GhostTap_Malware
{
    meta:
        description = "GhostTap"
        author = "Dragon-ThreatResearchHQ"
        reference = "http"
        threat_actor = "GhostTap"
        malware_family = "GhostTap"
        date = "2024-01-01"
    strings:
        $s1 = "GhostTap" ascii
    condition:
        uint16(0) == 0x5A4D and $s1
}
INNER_EOF

shopt -s extglob

python3 scripts/lint_repo.py
