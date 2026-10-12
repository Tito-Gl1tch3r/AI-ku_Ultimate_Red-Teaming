#!/usr/bin/env python3
"""
Authentication Constraint Testing Utility
Purpose: Generate test cases to verify authentication constraint hypotheses in a lab.
Usage:
    python constraint_violation_tester.py --dry-run
Example:
    python constraint_violation_tester.py
"""
import string
import random
import os
import argparse

def generate_test_cases_for_constraints():
    """Generate passwords that test various constraint hypotheses"""
    tests = []
    
    # Test 1: Mixed case (to check case sensitivity)
    mixed_case_6 = [
        'ExampleA', 'TestAA', 'DemoAA', 'PassWd', 'UserCsA',
        'Example1', 'Test01', 'Demo01', 'Pass01', 'User01',
        'EXAMPLE1', 'TEST01', 'DEMO01', 'PASS01', 'USER01'
    ]
    
    mixed_case_8 = [
        'ExampleXYz', 'TestPass', 'DemoTest', 'Password',
        'Example2025', 'Test2025', 'Demo2025', 'Pass2025', 
        'EXAMPLE2025', 'TEST2025', 'DEMO2025', 'PASS2025',
        'ExampleTest', 'TestDemo', 'DemoUser', 'UserPass'
    ]
    
    # Test 2: Special characters (to check allowed character sets)
    special_6 = [
        'user@1', 'test@1', 'demo@1', 'pass@1', 'admin@1',
        'user#1', 'test#1', 'demo#1', 'pass#1', 'admin#1',
        'user$1', 'test$1', 'demo$1',
        'user!1', 'test!1', 'demo!1', 'pass!1', 'admin!1'
    ]
    
    special_8 = [
        'user@123', 'test@123', 'demo@123', 'pass@123',
        'user#123', 'test#123', 'demo#123', 'pass#123', 
        'user$123', 'test$123', 'demo$123', 'pass$123',
        'user!123', 'test!123', 'demo!123', 'pass!123',
        'password', 'Password', 'PASSWORD', 'passw0rd',
        'P@ssw0rd', 'p@ssw0rd', 'P@SSW0RD', 'Pa$$w0rd'
    ]
    
    # Test 3: Length violations
    short_tests = [
        # Shorter than common constraints
        'user', 'test', 'demo', 'pass', 'admin',  # 4 chars
        'user1', 'test1', 'demo1', 'pass1',      # 5 chars  
    ]
    
    long_tests = [
        # Longer than common constraints
        'userlongtest', 'testdemouser', 'passwordtest',  # 9+ chars
        'userxx2025', 'testuser123', 'demopass456',    # 9+ chars
    ]
    
    # Test 4: Common patterns (e.g., security terms, year-based)
    common_patterns_6 = [
        'secure', 'system', 'access', 'secret', 'cyber1',
        'infose', 'crypto', 'hash12', 'salt12', 'login1'
    ]
    
    common_patterns_8 = [
        'security', 'system25', 'accesskey', 'secretpwd',
        'cybersec', 'infosec1', 'cryptoxx', 'hashsalt',
        'loginpwd', 'testauth', 'demopass', 'fall2025'
    ]
    
    return {
        'mixed_case_6': mixed_case_6,
        'mixed_case_8': mixed_case_8, 
        'special_6': special_6,
        'special_8': special_8,
        'short_tests': short_tests,
        'long_tests': long_tests,
        'common_patterns_6': common_patterns_6,
        'common_patterns_8': common_patterns_8
    }

def generate_additional_test_patterns():
    """Generate additional test patterns based on common attack vectors"""
    
    # Hypothesis 1: Common dictionary words
    dictionary_words_6 = [
        'simple', 'secure', 'system', 'access', 'secret',
        'hidden', 'locked', 'opened', 'closed', 'safety'
    ]
    
    dictionary_words_8 = [
        'password', 'security', 'computer', 'internet', 
        'software', 'hardware', 'database', 'network',
        'firewall', 'antivirus', 'malware', 'spyware'
    ]
    
    # Hypothesis 2: Number-heavy patterns
    number_heavy_6 = [
        '123456', '654321', '000000', '111111', '222222',
        '123123', '456456', '789789', '147147', '258258'
    ]
    
    number_heavy_8 = [
        '12345678', '87654321', '00000000', '11111111',
        '12341234', '56785678', '90129012', '19901990',
        '20242024', '20252025', '66006600', '48204820'
    ]
    
    return {
        'dictionary_6': dictionary_words_6,
        'dictionary_8': dictionary_words_8,
        'numbers_6': number_heavy_6,
        'numbers_8': number_heavy_8
    }

def main(dry_run=True):
    """Generate authentication constraint test pools"""
    print("Generating authentication constraint test pools...")
    
    violations = generate_test_cases_for_constraints()
    hypotheses = generate_additional_test_patterns()
    
    # Create mixed pools for testing
    # Pool for 6-character constraints
    pool_6_char = (
        violations['mixed_case_6'][:10] +
        violations['special_6'][:10] + 
        violations['common_patterns_6'][:10] +
        hypotheses['dictionary_6'][:10] +
        hypotheses['numbers_6'][:10]
    )  # 50 total
    
    # Pool for 8-character constraints (primary)
    pool_8_char_primary = (
        violations['mixed_case_8'][:15] +
        violations['special_8'][:15] +
        violations['common_patterns_8'][:15] +
        hypotheses['dictionary_8'][:15] +
        hypotheses['numbers_8'][:15]
    )  # 75 total
    
    # Pool for 8-character constraints (secondary, different mix)
    pool_8_char_secondary = (
        violations['mixed_case_8'][8:16] +  # Different subset
        violations['special_8'][8:16] +
        violations['short_tests'] +
        violations['long_tests'] +
        hypotheses['dictionary_8'][8:] +    # Different subset
        hypotheses['numbers_8'][7:]
    )  # ~70 total
    
    if dry_run:
        print("DRY-RUN: Skipping file writes. Pools prepared in memory.")
        print(f"  6-character constraint tests: {len(pool_6_char)} passwords")
        print(f"  8-character primary constraint tests: {len(pool_8_char_primary)} passwords")  
        print(f"  8-character secondary constraint tests: {len(pool_8_char_secondary)} passwords")
        return
    
    # Ensure entropy_pools directory exists
    output_dir = 'entropy_pools'
    os.makedirs(output_dir, exist_ok=True)

    # Save pools
    with open(os.path.join(output_dir, '6_char_constraint_tests.txt'), 'w') as f:
        f.write('\n'.join(pool_6_char))
    
    with open(os.path.join(output_dir, '8_char_primary_constraint_tests.txt'), 'w') as f:
        f.write('\n'.join(pool_8_char_primary))
        
    with open(os.path.join(output_dir, '8_char_secondary_constraint_tests.txt'), 'w') as f:
        f.write('\n'.join(pool_8_char_secondary))
    
    print(f"Generated constraint test pools:")
    print(f"  6-character constraint tests: {len(pool_6_char)} passwords")
    print(f"  8-character primary constraint tests: {len(pool_8_char_primary)} passwords")  
    print(f"  8-character secondary constraint tests: {len(pool_8_char_secondary)} passwords")
    print(f"  Total new test passwords: {len(pool_6_char) + len(pool_8_char_primary) + len(pool_8_char_secondary)}")
    
    # Show samples
    print(f"\nSample 6-character tests:")
    for i, pwd in enumerate(pool_6_char[:5]):
        print(f"  {i+1}. {pwd}")
    print(f"\nSample 8-character primary tests:")
    for i, pwd in enumerate(pool_8_char_primary[:5]):
        print(f"  {i+1}. {pwd}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auth constraint test generator (lab-only)")
    parser.add_argument("--dry-run", action="store_true", default=True)
    args = parser.parse_args()
    main(dry_run=args.dry_run)
