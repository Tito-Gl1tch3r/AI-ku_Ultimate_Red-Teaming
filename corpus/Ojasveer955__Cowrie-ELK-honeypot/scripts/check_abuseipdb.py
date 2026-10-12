#!/usr/bin/env python3
import os
import json
import requests
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ABUSEIPDB_API_KEY")
if not API_KEY:
    print("Error: ABUSEIPDB_API_KEY not set in environment")
    exit(1)

BASE_DIR = Path(__file__).parent.parent
LOG_DIR = BASE_DIR / "cowrie_logs"
CACHE_FILE = BASE_DIR / "abuseipdb_cache.json"

def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def get_unique_ips():
    ips = set()
    for log_file in LOG_DIR.glob("*.json*"):
        with open(log_file, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    ip = data.get("src_ip")
                    if ip:
                        ips.add(ip)
                except json.JSONDecodeError:
                    continue
    return ips

def check_ip(ip):
    url = "https://api.abuseipdb.com/api/v2/check"
    headers = {"Accept": "application/json", "Key": API_KEY}
    params = {"ipAddress": ip, "maxAgeInDays": 90}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json().get("data", {})

def main():
    cache = load_cache()
    ips = get_unique_ips()
    for ip in ips:
        if ip not in cache:
            print(f"Checking {ip}")
            data = check_ip(ip)
            cache[ip] = {
                "abuseConfidenceScore": data.get("abuseConfidenceScore"),
                "lastReportedAt": data.get("lastReportedAt"),
                "raw": data
            }
            time.sleep(1)
    save_cache(cache)

if __name__ == "__main__":
    main()
