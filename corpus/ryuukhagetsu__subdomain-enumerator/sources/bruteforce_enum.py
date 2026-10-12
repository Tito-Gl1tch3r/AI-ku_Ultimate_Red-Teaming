#!/usr/bin/env python3
"""
Bruteforce Subdomain Enumeration Module
Uses DNS resolution to bruteforce subdomains using wordlists
"""

import dns.resolver
import concurrent.futures
import os
import requests
from threading import Lock
import time

class BruteforceEnumerator:
    def __init__(self, domain, timeout=10, threads=50):
        self.domain = domain
        self.timeout = timeout
        self.threads = threads
        self.found_subdomains = set()
        self.lock = Lock()
        
        # Configure DNS resolver
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = timeout
        self.resolver.lifetime = timeout
        
        # Use multiple DNS servers for better reliability
        self.resolver.nameservers = [
            '8.8.8.8',      # Google
            '8.8.4.4',      # Google
            '1.1.1.1',      # Cloudflare
            '1.0.0.1',      # Cloudflare
            '208.67.222.222', # OpenDNS
            '208.67.220.220'  # OpenDNS
        ]
    
    def get_default_wordlist(self):
        """Get default wordlist from SecLists or create a basic one"""
        wordlists = [
            # SecLists paths (common locations)
            '/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt',
            '/opt/SecLists/Discovery/DNS/subdomains-top1million-5000.txt',
            '~/SecLists/Discovery/DNS/subdomains-top1million-5000.txt',
            './wordlists/subdomains-top1million-5000.txt',
            
            # Alternative wordlists
            '/usr/share/seclists/Discovery/DNS/bitquark-subdomains-top100000.txt',
            '/opt/SecLists/Discovery/DNS/bitquark-subdomains-top100000.txt',
            './wordlists/bitquark-subdomains-top100000.txt',
            
            # Smaller wordlists
            '/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt',
            './wordlists/common-subdomains.txt'
        ]
        
        # Try to find existing wordlist
        for wordlist_path in wordlists:
            expanded_path = os.path.expanduser(wordlist_path)
            if os.path.exists(expanded_path):
                print(f"Using wordlist: {expanded_path}")
                return expanded_path
        
        # Download wordlist if not found
        return self.download_wordlist()
    
    def download_wordlist(self):
        """Download wordlist from SecLists GitHub if not found locally"""
        wordlist_dir = "wordlists"
        os.makedirs(wordlist_dir, exist_ok=True)
        
        wordlist_path = os.path.join(wordlist_dir, "subdomains-top1million-5000.txt")
        
        if os.path.exists(wordlist_path):
            return wordlist_path
        
        print("Downloading default wordlist from SecLists...")
        
        try:
            url = "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                with open(wordlist_path, 'w') as f:
                    f.write(response.text)
                print(f"Wordlist downloaded to: {wordlist_path}")
                return wordlist_path
            else:
                print("Failed to download wordlist, using basic wordlist")
                return self.create_basic_wordlist()
                
        except Exception as e:
            print(f"Error downloading wordlist: {e}")
            return self.create_basic_wordlist()
    
    def create_basic_wordlist(self):
        """Create a basic wordlist if download fails"""
        wordlist_dir = "wordlists"
        os.makedirs(wordlist_dir, exist_ok=True)
        
        basic_wordlist = [
            "www", "mail", "ftp", "localhost", "webmail", "smtp", "pop", "ns1", "webdisk",
            "ns2", "cpanel", "whm", "autodiscover", "autoconfig", "m", "imap", "test",
            "ns", "blog", "pop3", "dev", "www2", "admin", "forum", "news", "vpn", "ns3",
            "mail2", "new", "mysql", "old", "lists", "support", "mobile", "mx", "static",
            "docs", "beta", "shop", "sql", "secure", "demo", "cp", "calendar", "wiki",
            "web", "media", "email", "images", "img", "www1", "intranet", "portal",
            "video", "sip", "dns2", "api", "cdn", "stats", "dns1", "ns4", "www3",
            "dns", "search", "staging", "server", "mx1", "chat", "wap", "my", "svn",
            "mail1", "sites", "proxy", "ads", "host", "crm", "cms", "backup", "mx2",
            "lyncdiscover", "info", "apps", "download", "remote", "db", "forums", "store",
            "relay", "files", "newsletter", "app", "live", "owa", "en", "start", "sms",
            "office", "exchange", "ipv4", "mail3", "help", "blogs", "helpdesk", "web1",
            "home", "library", "ftp2", "ntp", "monitor", "login", "service", "correo",
            "www4", "moodle", "webmail2", "link", "tracking", "ur", "bulletin", "catalogo",
            "board", "ns5", "redirect", "www5", "mx3", "secure2", "jdbc", "agenda",
            "www6", "test2", "ns6", "bbs", "online", "aws", "cloud", "lab", "s3"
        ]
        
        wordlist_path = os.path.join(wordlist_dir, "basic-subdomains.txt")
        
        with open(wordlist_path, 'w') as f:
            for word in basic_wordlist:
                f.write(f"{word}\n")
        
        print(f"Created basic wordlist: {wordlist_path}")
        return wordlist_path
    
    def load_wordlist(self, wordlist_path):
        """Load wordlist from file"""
        if not wordlist_path:
            wordlist_path = self.get_default_wordlist()
        
        if not os.path.exists(wordlist_path):
            print(f"Wordlist not found: {wordlist_path}")
            wordlist_path = self.get_default_wordlist()
        
        subdomains = []
        try:
            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    subdomain = line.strip().lower()
                    if subdomain and not subdomain.startswith('#'):
                        # Remove any existing domain suffix
                        if '.' in subdomain:
                            subdomain = subdomain.split('.')[0]
                        subdomains.append(subdomain)
            
            print(f"Loaded {len(subdomains)} subdomains from wordlist")
            return subdomains
            
        except Exception as e:
            print(f"Error loading wordlist: {e}")
            return []
    
    def resolve_subdomain(self, subdomain_prefix):
        """Resolve a single subdomain using DNS"""
        subdomain = f"{subdomain_prefix}.{self.domain}"
        
        try:
            # Try A record
            result = self.resolver.resolve(subdomain, 'A')
            if result:
                ips = [str(ip) for ip in result]
                with self.lock:
                    self.found_subdomains.add(subdomain)
                return subdomain, ips
                
        except dns.resolver.NXDOMAIN:
            # Subdomain doesn't exist
            pass
        except dns.resolver.NoAnswer:
            # No A record, try CNAME
            try:
                result = self.resolver.resolve(subdomain, 'CNAME')
                if result:
                    with self.lock:
                        self.found_subdomains.add(subdomain)
                    return subdomain, [str(result[0])]
            except:
                pass
        except dns.resolver.Timeout:
            # DNS timeout
            pass
        except Exception as e:
            # Other DNS errors
            pass
        
        return None, None
    
    def enumerate(self, wordlist_path=None):
        """Run bruteforce enumeration using wordlist"""
        print(f"Starting bruteforce enumeration for {self.domain}")
        
        # Load wordlist
        subdomain_prefixes = self.load_wordlist(wordlist_path)
        
        if not subdomain_prefixes:
            print("No valid wordlist found, skipping bruteforce enumeration")
            return set()
        
        print(f"Bruteforcing {len(subdomain_prefixes)} subdomains using {self.threads} threads...")
        
        # Progress tracking
        total = len(subdomain_prefixes)
        completed = 0
        found_count = 0
        start_time = time.time()
        
        def update_progress():
            nonlocal completed, found_count
            elapsed = time.time() - start_time
            rate = completed / elapsed if elapsed > 0 else 0
            print(f"Progress: {completed}/{total} ({completed/total*100:.1f}%) - Found: {found_count} - Rate: {rate:.1f}/s", end='\r')
        
        # Bruteforce with threading
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
            # Submit all tasks
            future_to_subdomain = {
                executor.submit(self.resolve_subdomain, prefix): prefix 
                for prefix in subdomain_prefixes
            }
            
            # Process results
            for future in concurrent.futures.as_completed(future_to_subdomain):
                subdomain_prefix = future_to_subdomain[future]
                try:
                    subdomain, ips = future.result()
                    completed += 1
                    
                    if subdomain:
                        found_count += 1
                        print(f"\n[+] Found: {subdomain} -> {', '.join(ips) if isinstance(ips, list) else ips}")
                    
                    # Update progress every 50 requests
                    if completed % 50 == 0:
                        update_progress()
                        
                except Exception as e:
                    completed += 1
                    # Silently continue on errors
                    pass
        
        # Final progress update
        elapsed = time.time() - start_time
        print(f"\nBruteforce completed: {found_count} subdomains found in {elapsed:.2f} seconds")
        
        return self.found_subdomains