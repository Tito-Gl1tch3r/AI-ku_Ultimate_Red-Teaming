#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

def run_script(script_name):
    script_path = Path(__file__).parent / script_name
    try:
        result = subprocess.run([sys.executable, str(script_path)], 
                              capture_output=True, text=True, check=True)
        print(f"✅ {script_name} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {script_name} failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

def main():
    print("🔍 Starting AbuseIPDB integration pipeline...")
    
    print("\n1. Checking AbuseIPDB for new IPs...")
    if not run_script("check_abuseipdb.py"):
        print("❌ AbuseIPDB check failed, stopping pipeline")
        return
    
    print("\n2. Enriching Cowrie logs with AbuseIPDB data...")
    if not run_script("enrich_cowrie_logs.py"):
        print("❌ Log enrichment failed")
        return
    
    print("\n✅ Pipeline completed successfully!")
    print("📊 Enriched logs are ready for ELK ingestion")

if __name__ == "__main__":
    main()
