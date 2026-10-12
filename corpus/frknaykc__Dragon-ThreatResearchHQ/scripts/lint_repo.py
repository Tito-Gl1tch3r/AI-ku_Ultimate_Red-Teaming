#!/usr/bin/env python3
"""
Dragon-ThreatResearchHQ Repository Linter & Quality Auditor
Audits all threat entries across APT-Groups, Malware, C2-Frameworks, and Campaigns
to ensure they meet the "Gold Standard" specification:
  - README.md (Metadata & Profile)
  - report.md (Detailed Analysis)
  - iocs.csv (Standard-compliant IOCs)
  - mitre_attack.md (MITRE ATT&CK Mapping)
  - fingerprints.txt (Hunting Queries: Shodan, Censys, SIEM)
  - yara/ (Detection Rules)
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

STANDARD_FILES = {
    "readme": "README.md",
    "report": "report.md",
    "iocs": "iocs.csv",
    "mitre": "mitre_attack.md",
    "fingerprints": "fingerprints.txt",
    "yara": "yara",
}

def scan_entries():
    entries = []

    # APT-Groups: Each direct child folder
    apt_dir = REPO_ROOT / "APT-Groups"
    if apt_dir.exists():
        for d in sorted(apt_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                entries.append(("APT", d))

    # Malware: subcategories (Stealers, RATs, Loaders, Backdoors, Miners, Wipers, Ransomware, etc.)
    malware_dir = REPO_ROOT / "Malware"
    if malware_dir.exists():
        for subcat in sorted(malware_dir.iterdir()):
            if subcat.is_dir() and not subcat.name.startswith("."):
                for d in sorted(subcat.iterdir()):
                    if d.is_dir() and not d.name.startswith("."):
                        entries.append((f"Malware/{subcat.name}", d))

    # Ransomware: Top-level category
    rw_dir = REPO_ROOT / "Ransomware"
    if rw_dir.exists():
        for d in sorted(rw_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                entries.append(("Ransomware", d))

    # C2-Frameworks: Each direct child folder
    c2_dir = REPO_ROOT / "C2-Frameworks"
    if c2_dir.exists():
        for d in sorted(c2_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                entries.append(("C2", d))

    # Campaigns: Each direct child folder
    camp_dir = REPO_ROOT / "Campaigns"
    if camp_dir.exists():
        for d in sorted(camp_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                entries.append(("Campaign", d))

    return entries

def audit():
    entries = scan_entries()
    total_checks = 0
    passed_checks = 0

    print(f"{'CATEGORY':<20} | {'NAME':<30} | {'README':<6} | {'REPORT':<6} | {'IOCS':<6} | {'MITRE':<6} | {'FPRINT':<6} | {'YARA':<6} | {'SCORE':<5}")
    print("-" * 105)

    low_score_entries = []

    for cat, path in entries:
        results = {}
        for key, fname in STANDARD_FILES.items():
            target = path / fname
            exists = target.exists() and (target.is_file() or (target.is_dir() and any(target.iterdir())))
            results[key] = exists
            total_checks += 1
            if exists:
                passed_checks += 1

        score = sum(1 for v in results.values() if v)
        pct = int((score / len(STANDARD_FILES)) * 100)

        sym = lambda b: "  ✓   " if b else "  ✗   "
        print(f"{cat:<20} | {path.name:<30} | {sym(results['readme'])} | {sym(results['report'])} | {sym(results['iocs'])} | {sym(results['mitre'])} | {sym(results['fingerprints'])} | {sym(results['yara'])} | {pct:>3}%")

        if pct < 50:
            low_score_entries.append((cat, path.name, pct))

    overall_pct = int((passed_checks / total_checks) * 100) if total_checks else 0
    print("=" * 105)
    print(f"Total Entries Tracked: {len(entries)}")
    print(f"Overall Repository Compliance Score: {overall_pct}% ({passed_checks}/{total_checks} requirements met)")
    print(f"Entries requiring documentation attention (<50%): {len(low_score_entries)}")

if __name__ == "__main__":
    audit()
