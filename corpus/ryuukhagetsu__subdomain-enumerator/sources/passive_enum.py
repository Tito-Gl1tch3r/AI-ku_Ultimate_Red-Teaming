#!/usr/bin/env python3
"""
Passive Subdomain Enumeration Module
Uses multiple online sources to discover subdomains
"""

import requests
import json
import re
import time
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
import ssl
import socket
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class PassiveEnumerator:
    def __init__(self, domain, timeout=10):
        self.domain = domain
        self.timeout = timeout
        self.subdomains = set()
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set headers to avoid blocking
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def crt_sh(self):
        """Enumerate subdomains using crt.sh certificate transparency logs"""
        subdomains = set()
        try:
            url = f"https://crt.sh/?q=%.{self.domain}&output=json"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                for cert in data:
                    if 'name_value' in cert:
                        names = cert['name_value'].split('\n')
                        for name in names:
                            name = name.strip().lower()
                            if name.endswith(f'.{self.domain}') or name == self.domain:
                                # Remove wildcards
                                if name.startswith('*.'):
                                    name = name[2:]
                                subdomains.add(name)
        except Exception as e:
            print(f"Error with crt.sh: {e}")
        
        return subdomains
    
    def threatcrowd(self):
        """Enumerate subdomains using ThreatCrowd API"""
        subdomains = set()
        try:
            url = f"https://www.threatcrowd.org/searchApi/v2/domain/report/?domain={self.domain}"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if 'subdomains' in data:
                    for subdomain in data['subdomains']:
                        subdomain = subdomain.strip().lower()
                        if subdomain.endswith(f'.{self.domain}'):
                            subdomains.add(subdomain)
        except Exception as e:
            print(f"Error with ThreatCrowd: {e}")
        
        # Rate limiting
        time.sleep(1)
        return subdomains
    
    def virustotal(self):
        """Enumerate subdomains using VirusTotal (without API key - limited)"""
        subdomains = set()
        try:
            # Note: This method has limitations without API key
            # You can add API key support here if needed
            url = f"https://www.virustotal.com/vtapi/v2/domain/report"
            params = {
                'domain': self.domain,
                'apikey': 'your_api_key_here'  # Replace with actual API key
            }
            # For now, skip VirusTotal to avoid API key requirement
            pass
        except Exception as e:
            print(f"Error with VirusTotal: {e}")
        
        return subdomains
    
    def hackertarget(self):
        """Enumerate subdomains using HackerTarget API"""
        subdomains = set()
        try:
            url = f"https://api.hackertarget.com/hostsearch/?q={self.domain}"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                for line in response.text.split('\n'):
                    if ',' in line:
                        subdomain = line.split(',')[0].strip().lower()
                        if subdomain.endswith(f'.{self.domain}'):
                            subdomains.add(subdomain)
        except Exception as e:
            print(f"Error with HackerTarget: {e}")
        
        return subdomains
    
    def dnsdumpster(self):
        """Enumerate subdomains using DNSDumpster (web scraping)"""
        subdomains = set()
        try:
            # Get CSRF token first
            url = "https://dnsdumpster.com/"
            response = self.session.get(url, timeout=self.timeout)
            
            csrf_token = None
            if response.status_code == 200:
                csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]*)"', response.text)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
            
            if csrf_token:
                # Submit domain search
                data = {
                    'csrfmiddlewaretoken': csrf_token,
                    'targetip': self.domain,
                    'user': 'free'
                }
                
                response = self.session.post(url, data=data, timeout=self.timeout)
                
                if response.status_code == 200:
                    # Extract subdomains from response
                    pattern = r'([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*' + re.escape(self.domain)
                    matches = re.findall(pattern, response.text)
                    for match in matches:
                        if isinstance(match, tuple):
                            subdomain = match[0] + self.domain
                        else:
                            subdomain = match
                        
                        subdomain = subdomain.strip().lower()
                        if subdomain.endswith(f'.{self.domain}') or subdomain == self.domain:
                            subdomains.add(subdomain)
        except Exception as e:
            print(f"Error with DNSDumpster: {e}")
        
        return subdomains
    
    def wayback_machine(self):
        """Enumerate subdomains using Wayback Machine API"""
        subdomains = set()
        try:
            url = f"http://web.archive.org/cdx/search/cdx?url=*.{self.domain}/*&output=json&fl=original&collapse=urlkey"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                for entry in data[1:]:  # Skip header
                    if entry and len(entry) > 0:
                        original_url = entry[0]
                        # Extract domain from URL
                        domain_match = re.search(r'https?://([^/]+)', original_url)
                        if domain_match:
                            extracted_domain = domain_match.group(1).lower()
                            if extracted_domain.endswith(f'.{self.domain}'):
                                subdomains.add(extracted_domain)
        except Exception as e:
            print(f"Error with Wayback Machine: {e}")
        
        return subdomains
    
    def anubis_db(self):
        """Enumerate subdomains using Anubis-DB API"""
        subdomains = set()
        try:
            url = f"https://jldc.me/anubis/subdomains/{self.domain}"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                for subdomain in data:
                    subdomain = subdomain.strip().lower()
                    if subdomain.endswith(f'.{self.domain}'):
                        subdomains.add(subdomain)
        except Exception as e:
            print(f"Error with Anubis-DB: {e}")
        
        return subdomains
    
    def alienvault(self):
        """Enumerate subdomains using AlienVault OTX API"""
        subdomains = set()
        try:
            url = f"https://otx.alienvault.com/api/v1/indicators/domain/{self.domain}/passive_dns"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if 'passive_dns' in data:
                    for record in data['passive_dns']:
                        if 'hostname' in record:
                            subdomain = record['hostname'].strip().lower()
                            if subdomain.endswith(f'.{self.domain}'):
                                subdomains.add(subdomain)
        except Exception as e:
            print(f"Error with AlienVault: {e}")
        
        return subdomains
    
    def rapiddns(self):
        """Enumerate subdomains using RapidDNS API"""
        subdomains = set()
        try:
            url = f"https://rapiddns.io/subdomain/{self.domain}?full=1"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                # Parse HTML response to extract subdomains
                pattern = r'([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+' + re.escape(self.domain)
                matches = re.findall(pattern, response.text)
                for match in matches:
                    if isinstance(match, tuple):
                        subdomain = match[0] + self.domain
                    else:
                        subdomain = match
                    
                    subdomain = subdomain.strip().lower()
                    if subdomain.endswith(f'.{self.domain}'):
                        subdomains.add(subdomain)
        except Exception as e:
            print(f"Error with RapidDNS: {e}")
        
        return subdomains
    
    def enumerate_all(self):
        """Run all passive enumeration methods concurrently"""
        methods = [
            self.crt_sh,
            self.threatcrowd,
            self.hackertarget,
            self.dnsdumpster,
            self.wayback_machine,
            self.anubis_db,
            self.alienvault,
            self.rapiddns
        ]
        
        all_subdomains = set()
        
        print(f"Running passive enumeration for {self.domain}...")
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_method = {executor.submit(method): method.__name__ for method in methods}
            
            for future in as_completed(future_to_method):
                method_name = future_to_method[future]
                try:
                    subdomains = future.result()
                    if subdomains:
                        print(f"  {method_name}: {len(subdomains)} subdomains")
                        all_subdomains.update(subdomains)
                    else:
                        print(f"  {method_name}: 0 subdomains")
                except Exception as e:
                    print(f"  {method_name}: Error - {e}")
        
        # Add the main domain
        all_subdomains.add(self.domain)
        
        return all_subdomains