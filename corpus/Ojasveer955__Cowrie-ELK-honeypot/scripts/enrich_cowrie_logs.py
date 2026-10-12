#!/usr/bin/env python3
import os
import json
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
CACHE_FILE = BASE_DIR / "abuseipdb_cache.json"
LOG_DIR = BASE_DIR / "cowrie_logs"
ENRICHED_DIR = BASE_DIR / "enriched_logs"

def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def enrich_log_entry(log_entry, abuse_cache):
    src_ip = log_entry.get("src_ip")
    if not src_ip:
        return log_entry
    
    abuse_data = abuse_cache.get(src_ip, {})
    if abuse_data:
        log_entry["abuseipdb"] = {
            "confidence_score": abuse_data.get("abuseConfidenceScore", 0),
            "last_reported": abuse_data.get("lastReportedAt"),
            "country_code": abuse_data.get("raw", {}).get("countryCode"),
            "isp": abuse_data.get("raw", {}).get("isp"),
            "is_tor": abuse_data.get("raw", {}).get("isTor", False),
            "total_reports": abuse_data.get("raw", {}).get("totalReports", 0),
            "usage_type": abuse_data.get("raw", {}).get("usageType")
        }
        
        confidence = abuse_data.get("abuseConfidenceScore", 0)
        if confidence == 100:
            log_entry["risk_level"] = "critical"
        elif confidence >= 75:
            log_entry["risk_level"] = "high"
        elif confidence >= 25:
            log_entry["risk_level"] = "medium"
        elif confidence > 0:
            log_entry["risk_level"] = "low"
        else:
            log_entry["risk_level"] = "unknown"
    
    return log_entry

def process_log_file(log_file, abuse_cache, output_file):
    processed_count = 0
    with open(log_file, "r") as infile, open(output_file, "w") as outfile:
        for line in infile:
            try:
                log_entry = json.loads(line.strip())
                enriched_entry = enrich_log_entry(log_entry, abuse_cache)
                outfile.write(json.dumps(enriched_entry) + "\n")
                processed_count += 1
            except json.JSONDecodeError:
                continue
    return processed_count

def main():
    ENRICHED_DIR.mkdir(exist_ok=True)
    abuse_cache = load_cache()
    print(f"Loaded {len(abuse_cache)} cached IP lookups")
    
    total_processed = 0
    for log_file in LOG_DIR.glob("*.json*"):
        if log_file.name.startswith("enriched_"):
            continue
            
        output_file = ENRICHED_DIR / f"enriched_{log_file.name}"
        print(f"Processing {log_file.name}...")
        
        count = process_log_file(log_file, abuse_cache, output_file)
        total_processed += count
        print(f"  Enriched {count} log entries -> {output_file.name}")
    
    print(f"Total processed: {total_processed} log entries")

if __name__ == "__main__":
    main()
