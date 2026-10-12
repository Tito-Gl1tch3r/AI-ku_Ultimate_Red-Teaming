#!/usr/bin/env python3
"""
Credential Reuse Analysis Tool
Purpose: Safely test a list of credentials across demo services to identify reuse vulnerabilities.
Usage:
    python credential_reuse.py --dry-run --user testuser --passwords file.txt
Example:
    python credential_reuse.py --dry-run --targets http://localhost:8083/login.html,http://localhost:8081/basicauth,http://localhost:8082/digestauth
"""

import requests
import base64
import hashlib
import time
from urllib.parse import quote
import argparse

class WebAuthTester:
    def __init__(self, target_urls=None, username=None, discovered_passwords=None, dry_run=True):
        self.html_url = target_urls.get('html_form', 'http://localhost/login.html') if target_urls else 'http://localhost/login.html'
        self.basic_url = target_urls.get('basic_auth', 'http://localhost/basicauth') if target_urls else 'http://localhost/basicauth'
        self.digest_url = target_urls.get('digest_auth', 'http://localhost/digestauth') if target_urls else 'http://localhost/digestauth'
        self.username = username if username else 'testuser'
        self.dry_run = dry_run
        
        self.discovered_passwords = discovered_passwords if discovered_passwords else []
        
        # Example of how to populate if needed for testing (remove for production)
        # self.discovered_passwords = [
        #     'password123', 'secret', 'admin', 'qwerty',
        #     'P@ssw0rd', 'MyPass1', 'SecurePwd!'
        # ]

    def test_html_form(self, password):
        """Test HTML form authentication"""
        if self.dry_run:
            return False, "DRY-RUN: Skipped HTML form request"
        try:
            response = requests.post(
                self.html_url,
                data={'httpd_username': self.username, 'httpd_password': password},
                timeout=10,
                allow_redirects=False
            )
            
            # Check for success indicators
            if response.status_code == 302:  # Redirect typically means success
                location = response.headers.get('Location', '')
                if 'success' in location.lower() or 'welcome' in location.lower():
                    return True, f"SUCCESS: Redirect to {location}"
            
            if response.status_code == 200:
                content = response.text.lower()
                if 'welcome' in content or 'success' in content or 'authenticated' in content:
                    return True, f"SUCCESS: Content indicates success"
                if 'invalid' in content or 'incorrect' in content or 'failed' in content:
                    return False, f"FAILED: Invalid credentials message"
            
            return False, f"Status: {response.status_code}"
            
        except Exception as e:
            return False, f"ERROR: {str(e)}"
    
    def test_basic_auth(self, password):
        """Test HTTP Basic authentication"""
        if self.dry_run:
            return False, "DRY-RUN: Skipped Basic auth request"
        try:
            auth_header = base64.b64encode(f"{self.username}:{password}".encode()).decode()
            
            response = requests.get(
                self.basic_url,
                headers={'Authorization': f'Basic {auth_header}'},
                timeout=10
            )
            
            if response.status_code == 200:
                return True, f"SUCCESS: Status 200, Content length: {len(response.text)}"
            elif response.status_code == 401:
                return False, f"FAILED: 401 Unauthorized"
            else:
                return False, f"Status: {response.status_code}"
                
        except Exception as e:
            return False, f"ERROR: {str(e)}"
    
    def get_digest_challenge(self):
        """Get digest authentication challenge"""
        if self.dry_run:
            return None
        try:
            response = requests.get(self.digest_url, timeout=10)
            if response.status_code == 401:
                auth_header = response.headers.get('WWW-Authenticate', '')
                if 'Digest' in auth_header:
                    return auth_header
            return None
        except:
            return None
    
    def test_digest_auth(self, password):
        """Test HTTP Digest authentication"""
        if self.dry_run:
            return False, "DRY-RUN: Skipped Digest auth request"
        try:
            # Get fresh challenge
            challenge = self.get_digest_challenge()
            if not challenge:
                return False, "ERROR: Could not get digest challenge"
            
            # Parse challenge (simplified)
            import re
            
            realm_match = re.search(r'realm="([^"]*)"', challenge)
            nonce_match = re.search(r'nonce="([^"]*)"', challenge)
            
            if not realm_match or not nonce_match:
                return False, "ERROR: Could not parse digest challenge"
            
            realm = realm_match.group(1)
            nonce = nonce_match.group(1)
            
            # Create digest response
            ha1 = hashlib.md5(f"{self.username}:{realm}:{password}".encode()).hexdigest()
            ha2 = hashlib.md5(f"GET:/digestauth".encode()).hexdigest()
            response_hash = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
            
            auth_header = (
                          f'Digest username="{self.username}", realm="{realm}", ' 
                          f'nonce="{nonce}", uri="/digestauth", ' 
                          f'response="{response_hash}"'
                          )
            
            response = requests.get(
                self.digest_url,
                headers={'Authorization': auth_header},
                timeout=10
            )
            
            if response.status_code == 200:
                return True, f"SUCCESS: Status 200, Content length: {len(response.text)}"
            elif response.status_code == 401:
                return False, f"FAILED: 401 Unauthorized"
            else:
                return False, f"Status: {response.status_code}"
                
        except Exception as e:
            return False, f"ERROR: {str(e)}"
    
    def run_all_tests(self):
        """Run all credential reuse tests"""
        results = {
            'html': [],
            'basic': [],
            'digest': []
        }
        
        if not self.discovered_passwords:
            print("No passwords provided for testing. Exiting.")
            return results

        mode = "DRY-RUN" if self.dry_run else "ACTIVE"
        print(f"Credential Reuse Testing ({mode})")
        print("=" * 50)
        print(f"Testing {len(self.discovered_passwords)} provided passwords...")
        print()
        
        for i, password in enumerate(self.discovered_passwords, 1):
            print(f"[{i:2d}/{len(self.discovered_passwords)}] Testing password: '{password}'")
            
            # Test HTML form
            success, msg = self.test_html_form(password)
            results['html'].append((password, success, msg))
            print(f"  HTML Form:  {msg}")
            time.sleep(0.1)
            
            # Test Basic auth
            success, msg = self.test_basic_auth(password)
            results['basic'].append((password, success, msg))
            print(f"  Basic Auth: {msg}")
            time.sleep(0.1)
            
            # Test Digest auth (only for 6-character alphanumeric passwords)
            if len(password) == 6 and password.isalnum():
                success, msg = self.test_digest_auth(password)
                results['digest'].append((password, success, msg))
                print(f"  Digest Auth: {msg}")
            else:
                results['digest'].append((password, False, "SKIPPED: Does not match 6-char alphanumeric format"))
                print(f"  Digest Auth: SKIPPED (format mismatch)")
            
            print()
            time.sleep(0.2)
        
        print("=" * 50)
        print("CREDENTIAL REUSE TEST COMPLETE")
        print("=" * 50)
        
        return results


def _parse_cli_args():
    parser = argparse.ArgumentParser(description="Credential Reuse Analysis Tool (lab-only)")
    parser.add_argument("--targets", type=str, default="",
                        help="Comma-separated URLs html_form,basic_auth,digest_auth")
    parser.add_argument("--user", type=str, default="testuser")
    parser.add_argument("--passwords", type=str, default="",
                        help="Path to newline-delimited password list")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Run without sending network requests (default)")
    return parser.parse_args()


def _build_targets_map(targets_str):
    if not targets_str:
        return {}
    parts = [p.strip() for p in targets_str.split(",") if p.strip()]
    mapping = {}
    if len(parts) > 0:
        mapping['html_form'] = parts[0]
    if len(parts) > 1:
        mapping['basic_auth'] = parts[1]
    if len(parts) > 2:
        mapping['digest_auth'] = parts[2]
    return mapping


if __name__ == "__main__":
    args = _parse_cli_args()
    passwords = []
    if args.passwords:
        try:
            with open(args.passwords, "r", encoding="utf-8") as fh:
                passwords = [line.strip() for line in fh if line.strip()]
        except Exception as e:
            print(f"Could not read passwords file: {e}")
    targets = _build_targets_map(args.targets)
    tester = WebAuthTester(target_urls=targets, username=args.user, discovered_passwords=passwords, dry_run=args.dry_run)
    tester.run_all_tests()
