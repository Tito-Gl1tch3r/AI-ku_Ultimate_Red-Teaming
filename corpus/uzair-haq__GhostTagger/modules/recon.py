#!/usr/bin/env python3
"""
GhostTagger Reconnaissance Module
Handles subdomain enumeration, technology fingerprinting, and endpoint discovery
"""

import requests
import socket
import dns.resolver
import subprocess
import re
import time
from urllib.parse import urljoin, urlparse
from colorama import Fore, Style
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class ReconModule:
    def __init__(self, timeout=10, threads=20):
        self.timeout = timeout
        self.threads = threads
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def subdomain_enumeration(self, domain):
        """Enumerate subdomains using common wordlist and DNS queries"""
        print(Fore.CYAN + f"[RECON] Starting subdomain enumeration for {domain}")
        
        subdomains = set()
        
        # Common subdomain wordlist
        common_subs = [
            'www', 'mail', 'ftp', 'localhost', 'webmail', 'smtp', 'pop', 'ns1', 'webdisk',
            'ns2', 'cpanel', 'whm', 'autodiscover', 'autoconfig', 'mx', 'test', 'dev',
            'staging', 'admin', 'api', 'blog', 'shop', 'forum', 'support', 'secure',
            'ssl', 'vpn', 'remote', 'demo', 'beta', 'alpha', 'mobile', 'm', 'wap',
            'portal', 'app', 'apps', 'download', 'downloads', 'static', 'cdn', 'media',
            'images', 'img', 'video', 'videos', 'assets', 'files', 'docs', 'help',
            'wiki', 'news', 'old', 'new', 'backup', 'bak', 'temp', 'tmp', 'archive',
            'git', 'svn', 'cvs', 'db', 'database', 'sql', 'mysql', 'postgres', 'oracle'
        ]
        
        def check_subdomain(sub):
            subdomain = f"{sub}.{domain}"
            try:
                # Try DNS resolution
                dns.resolver.resolve(subdomain, 'A')
                subdomains.add(subdomain)
                print(Fore.GREEN + f"[+] Found subdomain: {subdomain}")
                return subdomain
            except:
                pass
            return None
        
        # Use ThreadPoolExecutor for concurrent subdomain checking
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = [executor.submit(check_subdomain, sub) for sub in common_subs]
            for future in as_completed(futures):
                result = future.result()
        
        print(Fore.YELLOW + f"[RECON] Found {len(subdomains)} subdomains for {domain}")
        return list(subdomains)
    
    def technology_fingerprinting(self, url):
        """Fingerprint web technologies used by the target"""
        print(Fore.CYAN + f"[RECON] Fingerprinting technologies for {url}")
        
        technologies = {
            'server': 'Unknown',
            'cms': 'Unknown',
            'framework': 'Unknown',
            'language': 'Unknown',
            'database': 'Unknown',
            'headers': {}
        }
        
        try:
            response = self.session.get(url, timeout=self.timeout, verify=False)
            headers = response.headers
            content = response.text.lower()
            
            # Store all headers
            technologies['headers'] = dict(headers)
            
            # Server detection
            if 'server' in headers:
                technologies['server'] = headers['server']
            
            # CMS Detection
            cms_patterns = {
                'WordPress': ['wp-content', 'wp-includes', 'wp-admin'],
                'Joomla': ['joomla', '/administrator/', 'com_content'],
                'Drupal': ['drupal', 'sites/default', 'misc/drupal.js'],
                'Magento': ['magento', 'skin/frontend', 'js/mage'],
                'PrestaShop': ['prestashop', 'modules/blockcart'],
                'OpenCart': ['opencart', 'catalog/view'],
                'TYPO3': ['typo3', 'typo3conf'],
                'Concrete5': ['concrete5', 'concrete/css'],
                'ModX': ['modx', 'assets/modx']
            }
            
            for cms, patterns in cms_patterns.items():
                if any(pattern in content for pattern in patterns):
                    technologies['cms'] = cms
                    break
            
            # Framework Detection
            framework_patterns = {
                'Laravel': ['laravel_session', 'laravel_token'],
                'CodeIgniter': ['codeigniter', 'ci_session'],
                'Symfony': ['symfony', '_symfony'],
                'Zend': ['zend', 'zendframework'],
                'CakePHP': ['cakephp', 'cake_session'],
                'Django': ['django', 'csrfmiddlewaretoken'],
                'Flask': ['flask', 'werkzeug'],
                'Express.js': ['express', 'x-powered-by: express'],
                'Spring': ['spring', 'jsessionid'],
                'ASP.NET': ['asp.net', 'viewstate', '__dopostback']
            }
            
            for framework, patterns in framework_patterns.items():
                if any(pattern in content for pattern in patterns):
                    technologies['framework'] = framework
                    break
            
            # Language Detection
            if 'x-powered-by' in headers:
                powered_by = headers['x-powered-by'].lower()
                if 'php' in powered_by:
                    technologies['language'] = 'PHP'
                elif 'asp.net' in powered_by:
                    technologies['language'] = 'ASP.NET'
                elif 'express' in powered_by:
                    technologies['language'] = 'Node.js'
            
            # Additional language detection from content
            if '.php' in content or '<?php' in content:
                technologies['language'] = 'PHP'
            elif '.asp' in content or '.aspx' in content:
                technologies['language'] = 'ASP.NET'
            elif '.jsp' in content or 'jsessionid' in content:
                technologies['language'] = 'Java'
            elif '.py' in content or 'django' in content:
                technologies['language'] = 'Python'
            
            print(Fore.GREEN + f"[+] Server: {technologies['server']}")
            print(Fore.GREEN + f"[+] CMS: {technologies['cms']}")
            print(Fore.GREEN + f"[+] Framework: {technologies['framework']}")
            print(Fore.GREEN + f"[+] Language: {technologies['language']}")
            
        except Exception as e:
            print(Fore.RED + f"[-] Error fingerprinting {url}: {str(e)}")
        
        return technologies
    
    def endpoint_discovery(self, url):
        """Discover common endpoints and admin panels"""
        print(Fore.CYAN + f"[RECON] Discovering endpoints for {url}")
        
        found_endpoints = []
        
        # Common endpoints to check
        endpoints = [
            # Admin panels
            '/admin', '/admin/', '/administrator', '/administrator/', '/wp-admin',
            '/wp-admin/', '/admin.php', '/admin.html', '/login', '/login.php',
            '/login.html', '/panel', '/panel/', '/control', '/control/', '/manage',
            '/manage/', '/dashboard', '/dashboard/', '/cpanel', '/cpanel/',
            
            # Upload directories
            '/upload', '/uploads', '/upload.php', '/upload.html', '/files',
            '/files/', '/media', '/media/', '/assets', '/assets/', '/images',
            '/images/', '/img', '/img/', '/documents', '/documents/', '/docs',
            '/docs/', '/attachments', '/attachments/',
            
            # Common files
            '/robots.txt', '/sitemap.xml', '/.htaccess', '/web.config', '/crossdomain.xml',
            '/phpinfo.php', '/info.php', '/test.php', '/config.php', '/database.php',
            '/db.php', '/connect.php', '/connection.php', '/settings.php',
            
            # Backup files
            '/backup', '/backup/', '/backups', '/backups/', '/bak', '/bak/',
            '/old', '/old/', '/temp', '/temp/', '/tmp', '/tmp/', '/.git',
            '/.svn', '/.env', '/config.bak', '/database.bak', '/backup.sql',
            '/dump.sql', '/backup.zip', '/backup.tar.gz',
            
            # API endpoints
            '/api', '/api/', '/api/v1', '/api/v2', '/rest', '/rest/', '/graphql',
            '/webhook', '/webhooks', '/services', '/ws', '/rpc',
            
            # Development/Debug
            '/debug', '/test', '/dev', '/development', '/staging', '/beta',
            '/alpha', '/demo', '/phpMyAdmin', '/phpmyadmin', '/pma',
            '/adminer', '/adminer.php'
        ]
        
        def check_endpoint(endpoint):
            target_url = urljoin(url, endpoint)
            try:
                response = self.session.get(target_url, timeout=self.timeout, verify=False, allow_redirects=False)
                if response.status_code in [200, 301, 302, 403]:
                    found_endpoints.append({
                        'url': target_url,
                        'status': response.status_code,
                        'size': len(response.content),
                        'endpoint': endpoint
                    })
                    status_color = Fore.GREEN if response.status_code == 200 else Fore.YELLOW
                    print(status_color + f"[+] Found: {target_url} [{response.status_code}]")
                    return target_url
            except:
                pass
            return None
        
        # Use ThreadPoolExecutor for concurrent endpoint checking
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = [executor.submit(check_endpoint, endpoint) for endpoint in endpoints]
            for future in as_completed(futures):
                result = future.result()
        
        print(Fore.YELLOW + f"[RECON] Found {len(found_endpoints)} accessible endpoints")
        return found_endpoints
    
    def port_scan(self, host, ports=None):
        """Basic port scanning for common services"""
        if ports is None:
            ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 993, 995, 3306, 5432, 1433, 27017]
        
        print(Fore.CYAN + f"[RECON] Scanning ports for {host}")
        open_ports = []
        
        def scan_port(port):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((host, port))
                sock.close()
                if result == 0:
                    open_ports.append(port)
                    print(Fore.GREEN + f"[+] Port {port} is open")
                    return port
            except:
                pass
            return None
        
        # Use ThreadPoolExecutor for concurrent port scanning
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(scan_port, port) for port in ports]
            for future in as_completed(futures):
                result = future.result()
        
        print(Fore.YELLOW + f"[RECON] Found {len(open_ports)} open ports")
        return sorted(open_ports)
    
    def full_reconnaissance(self, target):
        """Perform full reconnaissance on a target"""
        print(Fore.MAGENTA + f"[RECON] Starting full reconnaissance for {target}")
        
        results = {
            'target': target,
            'subdomains': [],
            'technologies': {},
            'endpoints': [],
            'open_ports': []
        }
        
        # Parse target to get domain
        parsed = urlparse(target if target.startswith('http') else f'http://{target}')
        domain = parsed.netloc or parsed.path
        host = domain.split(':')[0]  # Remove port if present
        
        try:
            # Subdomain enumeration
            results['subdomains'] = self.subdomain_enumeration(host)
            
            # Technology fingerprinting
            results['technologies'] = self.technology_fingerprinting(target)
            
            # Endpoint discovery
            results['endpoints'] = self.endpoint_discovery(target)
            
            # Port scanning
            results['open_ports'] = self.port_scan(host)
            
        except Exception as e:
            print(Fore.RED + f"[-] Error during reconnaissance: {str(e)}")
        
        print(Fore.MAGENTA + f"[RECON] Reconnaissance completed for {target}")
        return results

