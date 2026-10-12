#!/usr/bin/env python3
"""
Advanced entropy generation using mathematical distribution sampling
Based on password research and failed attack analysis
"""
import random
import string
import hashlib
from itertools import product
import math

def hash_based_sampling(seed, length, count):
    """Generate passwords using hash-based pseudo-random sampling"""
    chars = string.ascii_lowercase + string.digits
    passwords = []
    
    for i in range(count):
        # Create unique seed for each password
        hash_input = f"{seed}_{i}_{length}"
        hash_obj = hashlib.sha256(hash_input.encode())
        hex_digest = hash_obj.hexdigest()
        
        # Convert hash to password
        password = ""
        for j in range(length):
            # Use different parts of hash for each character
            hex_chunk = hex_digest[j*2:(j*2)+2]
            char_index = int(hex_chunk, 16) % len(chars)
            password += chars[char_index]
        
        passwords.append(password)
    
    return passwords

def statistical_common_patterns_6char():
    """6-char patterns based on password statistics research"""
    patterns = []
    
    # Research shows these are statistically most common 6-char patterns
    # Based on analysis of leaked password databases
    
    # Dictionary words + numbers (most common pattern)
    words = ['love', 'pass', 'test', 'user', 'key', 'god', 'sex', 'dog', 'cat']
    for word in words:
        if len(word) == 4:
            for i in range(100):
                patterns.append(f"{word}{i:02d}")
        elif len(word) == 3:
            for i in range(100):
                patterns.append(f"{word}{i:03d}")
    
    # Names + birth years (very common)
    names = ['john', 'mike', 'dave', 'wang', 'test', 'demo']
    years = ['85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95']
    for name in names:
        for year in years:
            if len(name) + len(year) == 6:
                patterns.append(f"{name}{year}")
            elif len(name) == 4:
                patterns.append(f"{name}{year}")
    
    # Keyboard patterns (highly likely)
    keyboard = [
        'qwerty', 'asdfgh', 'zxcvbn', '123456', '654321',
        'qaz123', 'wsx234', 'edc345', 'rfv456', 'tgb567',
        'yhn678', 'ujm789', 'ik,890', 'ol.901', 'p;/012'
    ]
    patterns.extend(keyboard)
    
    # Course/academic specific
    academic = [
        'cs660a', 'cs660b', 'cs660c', 'jmu660', 'fall25', 'spr25',
        'test01', 'test02', 'test03', 'demo01', 'demo02', 'demo03',
        'wang01', 'wang02', 'wang03', 'admin1', 'admin2', 'admin3'
    ]
    patterns.extend(academic)
    
    # Simple substitutions of common words
    base_words = ['password', 'welcome', 'secret']
    for word in base_words:
        if len(word) >= 6:
            # Take first 6 chars and apply substitutions
            short = word[:6]
            patterns.append(short)
            # Common substitutions
            patterns.append(short.replace('a', '@'))
            patterns.append(short.replace('e', '3'))
            patterns.append(short.replace('o', '0'))
            patterns.append(short.replace('s', '5'))
    
    return list(set(patterns))[:100]

def statistical_common_patterns_8char():
    """8-char patterns based on password statistics research"""
    patterns = []
    
    # Dictionary word + 4 digits (extremely common)
    words = ['pass', 'love', 'test', 'user', 'home', 'work']
    for word in words:
        if len(word) == 4:
            # Years
            for year in range(1980, 2026):
                patterns.append(f"{word}{year}")
            # Other 4-digit patterns
            for digits in ['1234', '0000', '1111', '2222', '1337']:
                patterns.append(f"{word}{digits}")
    
    # 8-character dictionary words
    dict_words = [
        'password', 'computer', 'internet', 'security', 'welcome',
        'princess', 'sunshine', 'superman', 'football', 'baseball'
    ]
    patterns.extend(dict_words)
    
    # Academic/course patterns
    academic = [
        'cs660fall', 'cs660spr', 'jmu2025a', 'student1', 'student2',
        'wangpass', 'testpass', 'demopass', 'temppass', 'newpass',
        'cs660123', 'jmu66001', 'security', 'infosec1', 'cybersec'
    ]
    patterns.extend(academic)
    
    # Name + 4 digits
    names = ['wang', 'john', 'mike', 'test', 'demo', 'user']
    for name in names:
        if len(name) == 4:
            for year in ['2024', '2025', '1234', '0000']:
                patterns.append(f"{name}{year}")
    
    # Keyboard patterns
    keyboard_8 = [
        'qwertyui', 'asdfghjk', 'zxcvbnmq', 'qwerty12', 
        'password', 'asdf1234', 'qwer1234', '12345678'
    ]
    patterns.extend(keyboard_8)
    
    return list(set(patterns))[:100]

def birthday_paradox_sampling_6char(count=100):
    """Use birthday paradox principle for 6-char sampling"""
    # Birthday paradox: with ~1800 random samples, 50% chance of collision
    # in 6-char space, suggesting clustering around certain values
    chars = string.ascii_lowercase + string.digits
    
    passwords = []
    # Generate based on time-based seeds to create natural clustering
    for i in range(count):
        seed = hash(f"birthday_{i}") % (36**3)  # Cluster in smaller space
        password = ""
        for j in range(6):
            char_idx = (seed + j * 1000) % 36
            password += chars[char_idx]
        passwords.append(password)
    
    return passwords

def markov_chain_sampling_8char(count=100):
    """Use Markov chain principles for realistic 8-char generation"""
    # Based on English letter frequency and common password patterns
    
    # English letter frequency (approximate)
    letter_freq = {
        'a': 0.08167, 'b': 0.01492, 'c': 0.02782, 'd': 0.04253,
        'e': 0.12702, 'f': 0.02228, 'g': 0.02015, 'h': 0.06094,
        'i': 0.06966, 'j': 0.00153, 'k': 0.00772, 'l': 0.04025,
        'm': 0.02406, 'n': 0.06749, 'o': 0.07507, 'p': 0.01929,
        'q': 0.00095, 'r': 0.05987, 's': 0.06327, 't': 0.09056,
        'u': 0.02758, 'v': 0.00978, 'w': 0.02360, 'x': 0.00150,
        'y': 0.01974, 'z': 0.00074
    }
    
    passwords = []
    letters = list(letter_freq.keys())
    weights = list(letter_freq.values())
    
    for _ in range(count):
        password = ""
        for i in range(8):
            if i < 4:  # First 4 chars: weighted by frequency
                password += random.choices(letters, weights=weights)[0]
            else:  # Last 4 chars: numbers more likely
                if random.random() < 0.7:  # 70% chance of number
                    password += random.choice('0123456789')
                else:
                    password += random.choices(letters, weights=weights)[0]
        passwords.append(password)
    
    return passwords

def main():
    """Generate advanced entropy pools"""
    print("Generating advanced entropy pools based on statistical analysis...")
    
    # Generate new pools
    statistical_6 = statistical_common_patterns_6char()
    statistical_8 = statistical_common_patterns_8char()
    birthday_6 = birthday_paradox_sampling_6char(100)
    markov_8 = markov_chain_sampling_8char(100)
    hash_6 = hash_based_sampling("digest_v2", 6, 100)
    hash_8_html = hash_based_sampling("html_v2", 8, 100) 
    hash_8_basic = hash_based_sampling("basic_v2", 8, 100)
    
    # Save new pools
    with open('entropy_pools/statistical_6char.txt', 'w') as f:
        f.write('\n'.join(statistical_6))
    
    with open('entropy_pools/statistical_8char.txt', 'w') as f:
        f.write('\n'.join(statistical_8))
        
    with open('entropy_pools/birthday_6char.txt', 'w') as f:
        f.write('\n'.join(birthday_6))
        
    with open('entropy_pools/markov_8char.txt', 'w') as f:
        f.write('\n'.join(markov_8))
    
    # Create optimized combined pools for next attack round
    with open('entropy_pools/digest_v2_combined.txt', 'w') as f:
        combined = statistical_6[:50] + birthday_6[:50] + hash_6[:50]  # 150 total
        f.write('\n'.join(combined))
    
    with open('entropy_pools/html_v2_combined.txt', 'w') as f:
        combined = statistical_8[:50] + markov_8[:50] + hash_8_html[:50]  # 150 total
        f.write('\n'.join(combined))
        
    with open('entropy_pools/basic_v2_combined.txt', 'w') as f:
        combined = statistical_8[50:] + markov_8[50:] + hash_8_basic[:50]  # 150 total
        f.write('\n'.join(combined))
    
    print(f"Generated advanced pools:")
    print(f"  Statistical 6-char: {len(statistical_6)} passwords")
    print(f"  Statistical 8-char: {len(statistical_8)} passwords")
    print(f"  Birthday paradox 6-char: {len(birthday_6)} passwords")
    print(f"  Markov chain 8-char: {len(markov_8)} passwords")
    print(f"  Hash-based sampling: {len(hash_6)} + {len(hash_8_html)} + {len(hash_8_basic)}")
    print(f"  Combined attack pools: 150 passwords each")

if __name__ == "__main__":
    main()