#!/usr/bin/env python3
"""
Domain Validation Module
Validates domain names and subdomains
"""

import re
import socket
import tldextract

class DomainValidator:
    def __init__(self):
        # Domain regex pattern
        self.domain_pattern = re.compile(
            r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
        )
        
        # Subdomain regex pattern
        self.subdomain_pattern = re.compile(
            r'^(?:[a-zA-Z0-9_](?:[a-zA-Z0-9\-_]{0,61}[a-zA-Z0-9_])?\.)+[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
        )
        
        # Invalid characters for domains
        self.invalid_chars = set(['<', '>', '"', "'", '&', '\\', '/', ':', ';', '?', '#', '@', '=', '+', '$', ',', '[', ']', '{', '}', '|', '^', '`', '~'])
        
        # Common false positive patterns
        self.false_positive_patterns = [
            r'.*\.(png|jpg|jpeg|gif|css|js|ico|svg|woff|woff2|ttf|eot)$',
            r'.*\.(pdf|doc|docx|xls|xlsx|zip|rar|tar|gz)$',
            r'.*\.(mp3|mp4|avi|mov|wmv|flv|wav)$',
            r'^\d+\.\d+\.\d+\.\d+$',  # IP addresses
            r'^.*\.(local|localhost|test|example|invalid)$',
            r'^.*\.(onion)$',  # Tor domains
        ]
    
    def is_valid_domain(self, domain):
        """Validate if a string is a valid domain name"""
        if not domain or not isinstance(domain, str):
            return False
        
        # Basic checks
        domain = domain.strip().lower()
        
        # Length check
        if len(domain) > 253 or len(domain) < 3:
            return False
        
        # Character check
        if any(char in self.invalid_chars for char in domain):
            return False
        
        # Cannot start or end with hyphen or dot
        if domain.startswith('-') or domain.endswith('-'):
            return False
        if domain.startswith('.') or domain.endswith('.'):
            return False
        
        # Cannot have consecutive dots
        if '..' in domain:
            return False
        
        # Must have at least one dot
        if '.' not in domain:
            return False
        
        # Regex validation
        if not self.domain_pattern.match(domain):
            return False
        
        # Check if it's a false positive
        if self.is_false_positive(domain):
            return False
        
        # Check TLD validity using tldextract
        try:
            extracted = tldextract.extract(domain)
            if not extracted.suffix:
                return False
        except:
            return False
        
        return True
    
    def is_valid_subdomain(self, subdomain):
        """Validate if a string is a valid subdomain"""
        if not subdomain or not isinstance(subdomain, str):
            return False
        
        # Basic checks
        subdomain = subdomain.strip().lower()
        
        # Length check
        if len(subdomain) > 253 or len(subdomain) < 3:
            return False
        
        # Character check
        if any(char in self.invalid_chars for char in subdomain):
            return False
        
        # Cannot start or end with hyphen or dot
        if subdomain.startswith('-') or subdomain.endswith('-'):
            return False
        if subdomain.startswith('.') or subdomain.endswith('.'):
            return False
        
        # Cannot have consecutive dots
        if '..' in subdomain:
            return False
        
        # Must have at least one dot
        if '.' not in subdomain:
            return False
        
        # Check for wildcard patterns
        if subdomain.startswith('*.'):
            subdomain = subdomain[2:]
        
        # Regex validation
        if not self.subdomain_pattern.match(subdomain):
            return False
        
        # Check if it's a false positive
        if self.is_false_positive(subdomain):
            return False
        
        # Validate the root domain part
        parts = subdomain.split('.')
        if len(parts) < 2:
            return False
        
        # Check each part
        for part in parts:
            if not part:
                return False
            if len(part) > 63:
                return False
            if part.startswith('-') or part.endswith('-'):
                return False
        
        # Check TLD validity
        try:
            extracted = tldextract.extract(subdomain)
            if not extracted.suffix:
                return False
        except:
            return False
        
        return True
    
    def is_false_positive(self, domain):
        """Check if domain matches false positive patterns"""
        for pattern in self.false_positive_patterns:
            if re.match(pattern, domain, re.IGNORECASE):
                return True
        return False
    
    def normalize_domain(self, domain):
        """Normalize domain name"""
        if not domain:
            return None
        
        domain = domain.strip().lower()
        
        # Remove protocol if present
        if domain.startswith('http://'):
            domain = domain[7:]
        elif domain.startswith('https://'):
            domain = domain[8:]
        
        # Remove path if present
        if '/' in domain:
            domain = domain.split('/')[0]
        
        # Remove port if present
        if ':' in domain and not domain.count(':') > 1:  # Not IPv6
            domain = domain.split(':')[0]
        
        # Remove trailing dot
        if domain.endswith('.'):
            domain = domain[:-1]
        
        return domain
    
    def extract_root_domain(self, subdomain):
        """Extract root domain from subdomain"""
        try:
            extracted = tldextract.extract(subdomain)
            if extracted.domain and extracted.suffix:
                return f"{extracted.domain}.{extracted.suffix}"
            return None
        except:
            return None
    
    def is_subdomain_of(self, subdomain, domain):
        """Check if subdomain belongs to the given domain"""
        if not subdomain or not domain:
            return False
        
        subdomain = self.normalize_domain(subdomain)
        domain = self.normalize_domain(domain)
        
        if not subdomain or not domain:
            return False
        
        return subdomain.endswith(f'.{domain}') or subdomain == domain
    
    def get_subdomain_depth(self, subdomain):
        """Get the depth level of a subdomain"""
        if not subdomain:
            return 0
        
        subdomain = self.normalize_domain(subdomain)
        if not subdomain:
            return 0
        
        try:
            extracted = tldextract.extract(subdomain)
            if extracted.subdomain:
                return len(extracted.subdomain.split('.'))
            return 0
        except:
            return 0
    
    def is_ip_address(self, address):
        """Check if string is an IP address"""
        try:
            socket.inet_aton(address)
            return True
        except socket.error:
            try:
                socket.inet_pton(socket.AF_INET6, address)
                return True
            except socket.error:
                return False
    
    def sanitize_subdomain_list(self, subdomains):
        """Sanitize and validate a list of subdomains"""
        valid_subdomains = set()
        
        for subdomain in subdomains:
            if not subdomain:
                continue
            
            # Normalize
            normalized = self.normalize_domain(subdomain)
            if not normalized:
                continue
            
            # Validate
            if self.is_valid_subdomain(normalized):
                valid_subdomains.add(normalized)
        
        return list(valid_subdomains)
    
    def filter_subdomains_by_domain(self, subdomains, target_domain):
        """Filter subdomains to only include those belonging to target domain"""
        filtered = []
        
        for subdomain in subdomains:
            if self.is_subdomain_of(subdomain, target_domain):
                filtered.append(subdomain)
        
        return filtered
    
    def remove_duplicates(self, subdomains):
        """Remove duplicates and normalize subdomains"""
        normalized_set = set()
        
        for subdomain in subdomains:
            normalized = self.normalize_domain(subdomain)
            if normalized and self.is_valid_subdomain(normalized):
                normalized_set.add(normalized)
        
        return list(normalized_set)
    
    def sort_subdomains(self, subdomains):
        """Sort subdomains by depth and alphabetically"""
        def sort_key(subdomain):
            depth = self.get_subdomain_depth(subdomain)
            return (depth, subdomain)
        
        return sorted(subdomains, key=sort_key)