#!/usr/bin/env python3

import os
import re
import time
import subprocess
from datetime import datetime

def check_hydra_success():
    """Check Hydra logs for successful authentication"""
    html_logs = [
        'evidence/distributed/html.part00.log',
        'evidence/distributed/html.part01.log', 
        'evidence/distributed/html.part02.log',
        'evidence/distributed/html.part03.log'
    ]
    
    success_patterns = [
        r'\[80\]\[http-post-form\] host: .* login: .* password: .*',
        r'1 of 1 target successfully completed',
        r'login: .* password: .*'
    ]
    
    for log_file in html_logs:
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    for pattern in success_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        if matches:
                            return f"SUCCESS in {log_file}: {matches[-1]}"
            except Exception as e:
                continue
    return None

def check_patator_success():
    """Check if any patator processes have found success"""
    try:
        # Check if any patator process has exited with success (would quit due to -x quit:code=200)
        result = subprocess.run(['pgrep', '-f', 'patator.*quit:code=200'], 
                              capture_output=True, text=True)
        
        # If no patator processes running, they may have found success and quit
        if result.returncode != 0:
            return "POTENTIAL SUCCESS: Some patator processes have terminated (may have found 200 response)"
    except Exception as e:
        pass
    return None

def get_campaign_status():
    """Get overall campaign status"""
    try:
        # Count running processes
        hydra_count = subprocess.run(['pgrep', '-c', '-f', 'hydra.*192.168.100.101'], 
                                   capture_output=True, text=True)
        patator_count = subprocess.run(['pgrep', '-c', '-f', 'patator.*password=FILE0'], 
                                     capture_output=True, text=True)
        
        hydra_running = int(hydra_count.stdout.strip()) if hydra_count.returncode == 0 else 0
        patator_running = int(patator_count.stdout.strip()) if patator_count.returncode == 0 else 0
        
        return f"Hydra: {hydra_running} processes, Patator: {patator_running} processes"
    except:
        return "Status check failed"

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Campaign Monitor Starting")
    print("=" * 60)
    
    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking campaign status...")
        
        # Check for success indicators
        hydra_success = check_hydra_success()
        if hydra_success:
            print(f"🎯 HYDRA SUCCESS DETECTED: {hydra_success}")
            break
            
        patator_success = check_patator_success()
        if patator_success:
            print(f"🎯 PATATOR SUCCESS DETECTED: {patator_success}")
            # Don't break here, need to verify actual success
        
        # Show running status
        status = get_campaign_status()
        print(f"📊 Status: {status}")
        
        # Wait before next check
        time.sleep(30)
    
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Monitor stopped due to success detection")

if __name__ == "__main__":
    main()