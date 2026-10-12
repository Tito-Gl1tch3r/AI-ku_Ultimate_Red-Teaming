#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║                    BLOOD-WEB HONEYPOT v1.0                     ║
║         ╔═══════════════════════════════════════╗                ║
║         ║   "All that and a bag of chips..."    ║                ║
║         ║        Bela Dimitrescu               ║                ║
║         ╚═══════════════════════════════════════╝                ║
╚══════════════════════════════════════════════════════════════════╝

A realistic honeypot system for pentesting training.
Simulates fake targets with real attack simulation.

[!] FOR EDUCATIONAL PURPOSES ONLY - USE ON YOUR OWN NETWORK OR LAB

LEGAL NOTICE:
This tool is provided for educational purposes only.
- Use ONLY on your own infrastructure or in an isolated lab environment
- You are SOLELY responsible for your use of this tool
- Any unauthorized, illegal, or malicious use is strictly prohibited
- The author CANNOT be held liable for any misuse by third parties
- By using this tool, you accept these terms

See LEGAL.md for full legal disclaimer.
"""

import socket
import threading
import logging
import sys
import os
import time
import random
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class ServiceType(Enum):
    SSH = "ssh"
    FTP = "ftp"
    HTTP = "http"
    TELNET = "telnet"
    SMB = "smb"
    MYSQL = "mysql"
    RDP = "rdp"

@dataclass
class AttackLog:
    timestamp: str
    source_ip: str
    source_port: int
    service: str
    technique: str
    payload: str
    severity: str

class GothicTheme:
    """Bela Dimitrescu themed ASCII art and messages"""
    
    HEADER = """
    ██╗███╗   ██╗███████╗██╗   ██╗██████╗  ██████╗  █████╗ ██████╗ 
    ██║████╗  ██║██╔════╝██║   ██║██╔══██╗██╔═══██╗██╔══██╗██╔══██╗
    ██║██╔██╗ ██║█████╗  ██║   ██║██████╔╝██║   ██║███████║██████╔╝
    ██║██║╚██╗██║██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══██║██╔══██╗
    ██║██║ ╚████║██║     ╚██████╔╝██║  ██║╚██████╔╝██║  ██║██║  ██║
    ╚═╝╚═╝  ╚═══╝╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝
                    ~ W E B   H O N E Y P O T ~
    """
    
    CASTLE_ART = """
                    ╔═══════════════════════════════════════╗
                    ║    🏰  CASTLE of THE FOUR IMMORTALS  🏰    ║
                    ╚═══════════════════════════════════════╝
                          ║▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║
                        ╔═╝                    ╚═╗
                       ╔╝    ╔══════════╗        ╚═╗
                       ║     ║ ♛ ♛ ♛ ♛  ║         ║
                       ║     ╚══════════╝         ║
                      ╔╝                          ╚═╗
                     ╔╝        ╔════════╗           ╚═╗
                     ║         ║ 🔱 🔱 🔱║            ║
                     ║         ╚════════╝            ║
                    ╔╝                             ╚═╗
                   ╔╝           ╔════╗              ╚═╗
                   ║            ║ 👑 ║               ║
                   ║            ╚════╝               ║
        ▄▄▄▄▄▄▄▄▄▄▄▄▄▄╔══════════════════╗▄▄▄▄▄▄▄▄▄▄▄▄▄
        ════════════════╝  ░░░░░░░░░░░░░  ╚═══════════════
                    ═══════  BLOOD-WEB v1.0  ═══════
    """
    
    MOTTOES = [
        "All that and a bag of chips...",
        "The House of Dimitrescu welcomes you...",
        "Dinner is served, but first... let's play.",
        "The daughters are hungry...",
        "You shouldn't have come here...",
        "Mother knows best...",
        "How delightful to have you visit...",
        "Stay a while... and listen...",
    ]

class BloodWebHoneypot:
    """Main honeypot orchestrator"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.services: Dict[ServiceType, 'HoneypotService'] = {}
        self.attack_logs: List[AttackLog] = []
        self.running = False
        self.theme = GothicTheme()
        
        self._setup_logging()
        
    def _setup_logging(self):
        """Configure attack logging"""
        log_dir = self.config.get('log_dir', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f'attacks_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        
        self.logger = logging.getLogger('BloodWeb')
        self.logger.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter(
            '\033[91m[ATK]\033[0m %(message)s'
        ))
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
    def register_service(self, service: 'HoneypotService'):
        """Register a service to the honeypot"""
        self.services[service.service_type] = service
        service.set_logger(self.logger)
        
    def log_attack(self, attack: AttackLog):
        """Log an attack attempt"""
        self.attack_logs.append(attack)
        self.logger.info(
            f"{attack.source_ip}:{attack.source_port} -> {attack.service} | "
            f"{attack.technique} | Severity: {attack.severity} | Payload: {attack.payload[:50]}..."
        )
        
    def start(self):
        """Start all registered services"""
        print(self.theme.HEADER)
        print(f"\n\033[93m{random.choice(self.theme.MOTTOES)}\033[0m\n")
        print(self.theme.CASTLE_ART)
        
        self.running = True
        
        print(f"\n\033[92m[+]\033[0m Blood-Web Honeypot starting...")
        print(f"\033[92m[+]\033[0m Registered services: {len(self.services)}")
        
        threads = []
        for service_type, service in self.services.items():
            print(f"\033[92m[+]\033[0m Starting {service_type.value} honeypot on port {service.port}...")
            t = threading.Thread(target=service.start, daemon=True)
            threads.append(t)
            t.start()
            
        print(f"\n\033[92m[+]\033[0m All services active. Waiting for attacks...")
        print(f"\033[93m[!]\033[0m Press Ctrl+C to stop\n")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
            
    def stop(self):
        """Stop all services"""
        print("\n\033[91m[!]\033[0m Shutting down Blood-Web...")
        self.running = False
        for service in self.services.values():
            service.stop()
        print("\033[92m[+]\033[0m Blood-Web stopped.")
        sys.exit(0)


class HoneypotService:
    """Base class for honeypot services"""
    
    def __init__(self, service_type: ServiceType, port: int):
        self.service_type = service_type
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.logger = None
        self.running = False
        self.theme = GothicTheme()
        
    def set_logger(self, logger):
        self.logger = logger
        
    def start(self):
        """Start the service"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.socket.bind(('0.0.0.0', self.port))
        except OSError as e:
            if e.errno == 98:
                print(f"""
\033[91m[!]\033[0m Port {self.port} ({self.service_type.value}) déjà utilisé.

\033[93m[?]\033[0m Pour voir quel processus utilise ce port:
    sudo lsof -i:{self.port}

\033[93m[>]\033[0m Pour libérer le port (uniquement si c'est blood-web):
    pkill -f blood-web.py

\033[93m[>]\033[0m Ou lance blood-web sur d'autres ports:
    python3 blood-web.py --custom-ports 5522 5521 5800 5523 5445 53306 53389
""")
                return
        self.socket.listen(5)
        self.running = True
        
        while self.running:
            try:
                client_socket, addr = self.socket.accept()
                threading.Thread(
                    target=self._handle_connection,
                    args=(client_socket, addr),
                    daemon=True
                ).start()
            except Exception as e:
                if self.running:
                    pass
                    
    def stop(self):
        """Stop the service"""
        self.running = False
        if self.socket:
            self.socket.close()
            
    def _handle_connection(self, client: socket.socket, addr: tuple):
        """Handle incoming connection - override in subclass"""
        raise NotImplementedError
        
    def log_attack(self, addr: tuple, technique: str, payload: str, severity: str = "MEDIUM"):
        """Log an attack"""
        attack = AttackLog(
            timestamp=datetime.now().isoformat(),
            source_ip=addr[0],
            source_port=addr[1],
            service=self.service_type.value,
            technique=technique,
            payload=payload[:200],
            severity=severity
        )
        if self.logger:
            self.logger.info(
                f"{addr[0]}:{addr[1]} -> {self.service_type.value} | "
                f"{technique} | {severity} | {payload[:50]}..."
            )


class SSHHoneypot(HoneypotService):
    """SSH honeypot - simulates OpenSSH with realistic behavior"""
    
    def __init__(self, port: int = 22):
        super().__init__(ServiceType.SSH, port)
        self.banner = self._generate_realistic_banner()
        self.fake_users = self._generate_fake_users()
        
    def _generate_realistic_banner(self) -> str:
        """Generate a realistic SSH banner"""
        banners = [
            "SSH-2.0-OpenSSH_8.4p1 Debian-5+deb11u3",
            "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.4",
            "SSH-2.0-OpenSSH_7.4p1 Debian-10+deb9u7",
            "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5",
            "SSH-2.0-OpenSSH_for_Windows_8.1p1",
        ]
        return random.choice(banners)
        
    def _generate_fake_users(self) -> Dict[str, Dict]:
        """Generate realistic fake user data"""
        return {
            "admin": {"pass": "admin123", "home": "/home/admin", "shell": "/bin/bash"},
            "root": {"pass": "toor", "home": "/root", "shell": "/bin/bash"},
            "user": {"pass": "password", "home": "/home/user", "shell": "/bin/bash"},
            "ubuntu": {"pass": "ubuntu", "home": "/home/ubuntu", "shell": "/bin/bash"},
            "mysql": {"pass": "mysql", "home": "/var/lib/mysql", "shell": "/bin/false"},
            "backup": {"pass": "backup123", "home": "/backup", "shell": "/bin/bash"},
            "webadmin": {"pass": "web@dm1n", "home": "/var/www", "shell": "/bin/bash"},
            "deploy": {"pass": "deploy2024", "home": "/opt/deploy", "shell": "/bin/bash"},
            "jenkins": {"pass": "jenkins", "home": "/var/lib/jenkins", "shell": "/bin/bash"},
            "tomcat": {"pass": "tomcat", "home": "/opt/tomcat", "shell": "/bin/bash"},
        }
        
    def _handle_connection(self, client: socket.socket, addr: tuple):
        """Handle SSH connection with realistic protocol simulation"""
        try:
            client.settimeout(30)
            
            # Send SSH banner
            client.send((self.banner + "\r\n").encode())
            
            # Handle SSH key exchange simulation
            data = b""
            while b"\r\n" not in data:
                chunk = client.recv(1024)
                if not chunk:
                    return
                data += chunk
                
            # Record connection attempt
            self.log_attack(
                addr,
                "SSH_CONNECTION",
                f"Banner exchange: {data[:50].decode('utf-8', errors='ignore')}",
                "LOW"
            )
            
            # Simulate key exchange
            client.send(b"SSH-2.0-OpenSSH_8.4\r\n")
            
            # Read client ID
            try:
                client_data = client.recv(4096)
                if client_data:
                    self.log_attack(
                        addr,
                        "SSH_CLIENT_VERSION",
                        client_data.decode('utf-8', errors='ignore').strip(),
                        "LOW"
                    )
            except:
                pass
                
            # Simulate multiple auth attempts
            attempts = 0
            for _ in range(random.randint(3, 8)):
                try:
                    auth_data = client.recv(4096)
                    if not auth_data:
                        break
                        
                    attempts += 1
                    
                    # Detect attack type
                    if b"ssh-rsa" in auth_data or b"ssh-dss" in auth_data or b"ecdsa" in auth_data:
                        technique = "SSH_KEY_EXCHANGE"
                        severity = "LOW"
                    elif b"password" in auth_data.lower():
                        # Extract potential credentials
                        try:
                            decoded = auth_data.decode('utf-8', errors='ignore')
                            if "password" in decoded.lower():
                                # Try to extract username
                                for user in self.fake_users:
                                    if user.encode() in auth_data:
                                        technique = f"SSH_AUTH_BRUTE_FORCE | User: {user}"
                                        severity = "HIGH"
                                        break
                                else:
                                    technique = "SSH_AUTH_ATTEMPT"
                                    severity = "MEDIUM"
                            else:
                                technique = "SSH_AUTH_EXCHANGE"
                                severity = "LOW"
                        except:
                            technique = "SSH_AUTH"
                            severity = "MEDIUM"
                    elif b"session" in auth_data.lower():
                        technique = "SSH_SESSION_INIT"
                        severity = "MEDIUM"
                    else:
                        technique = "SSH_PROTOCOL_DATA"
                        severity = "LOW"
                        
                    self.log_attack(
                        addr,
                        technique,
                        auth_data[:100].hex(),
                        severity
                    )
                    
                except socket.timeout:
                    break
                except Exception:
                    break
                    
            # Simulate authentication failure
            fail_response = self._generate_auth_failure()
            try:
                client.send(fail_response.encode())
            except:
                pass
                
        except Exception as e:
            self.log_attack(addr, "SSH_ERROR", str(e)[:100], "LOW")
        finally:
            try:
                client.close()
            except:
                pass
                
    def _generate_auth_failure(self) -> str:
        """Generate realistic auth failure message"""
        messages = [
            "Permission denied, please try again.\r\n",
            "Authentication failed.\r\n",
            "Access denied\r\n",
            "Too many authentication failures\r\n",
        ]
        return random.choice(messages)


class FTPHoneypot(HoneypotService):
    """FTP honeypot with realistic responses"""
    
    def __init__(self, port: int = 21):
        super().__init__(ServiceType.FTP, port)
        self.banner = "220 (vsFTPd 3.0.3)\r\n"
        self.fake_files = self._generate_fake_filesystem()
        
    def _generate_fake_filesystem(self) -> Dict:
        """Generate realistic fake file system"""
        return {
            "/": ["home", "var", "etc", "tmp", "opt", "usr"],
            "/home": ["admin", "ubuntu", "backup", "www-data"],
            "/home/admin": [".bashrc", ".ssh", "documents", "downloads"],
            "/home/admin/documents": ["report_2024.pdf", "credentials.txt", "server_config.yml", "database_backup.sql"],
            "/home/admin/.ssh": ["id_rsa", "id_rsa.pub", "authorized_keys", "known_hosts"],
            "/var/www": ["html", "logs", "backups"],
            "/var/www/html": ["index.html", "admin.php", ".htaccess"],
            "/etc": ["passwd", "shadow", "ssh", "nginx"],
            "/backup": ["backup_2024_01.tar.gz", "db_backup.sql", "config.tar"],
        }
        
    def _handle_connection(self, client: socket.socket, addr: tuple):
        """Handle FTP connection"""
        try:
            client.settimeout(60)
            client.send(self.banner.encode())
            
            self.log_attack(addr, "FTP_CONNECTION", "New FTP connection", "LOW")
            
            authenticated = False
            current_user = None
            current_dir = "/"
            
            while True:
                try:
                    cmd = client.recv(1024).decode('utf-8', errors='ignore').strip()
                    if not cmd:
                        break
                        
                    parts = cmd.split(maxsplit=1)
                    command = parts[0].upper() if parts else ""
                    arg = parts[1] if len(parts) > 1 else ""
                    
                    # Log the command
                    self.log_attack(
                        addr,
                        f"FTP_COMMAND:{command}",
                        cmd[:100],
                        "MEDIUM"
                    )
                    
                    # Detect credentials in command
                    if command == "USER":
                        current_user = arg
                        self.log_attack(
                            addr,
                            "FTP_USER_ENUMERATION",
                            f"Attempting user: {arg}",
                            "MEDIUM"
                        )
                        client.send("331 Please specify the password.\r\n".encode())
                        
                    elif command == "PASS":
                        self.log_attack(
                            addr,
                            "FTP_BRUTE_FORCE",
                            f"Password attempt for {current_user}: {arg}",
                            "HIGH"
                        )
                        # Always fail but simulate some attempts
                        if random.random() < 0.1:  # 10% chance of "success" to keep attacker engaged
                            client.send("230 Login successful.\r\n".encode())
                            authenticated = True
                        else:
                            client.send("530 Login incorrect.\r\n".encode())
                            
                    elif command == "SYST":
                        client.send("215 UNIX Type: L8\r\n".encode())
                        
                    elif command == "FEAT":
                        client.send("211-Features:\r\n EPRT\r\n EPSV\r\n MDTM\r\n PASV\r\n REST STREAM\r\n SIZE\r\n TVFS\r\n211 End\r\n".encode())
                        
                    elif command == "PWD":
                        client.send(f"257 \"{current_dir}\"\r\n".encode())
                        
                    elif command == "CWD":
                        new_dir = arg if arg.startswith("/") else current_dir.rstrip("/") + "/" + arg
                        if new_dir in self.fake_files or any(new_dir.startswith(p) for p in self.fake_files):
                            current_dir = new_dir
                            self.log_attack(addr, "FTP_DIR_TRAVERSAL", f"Navigating to: {new_dir}", "MEDIUM")
                            client.send("250 Directory successfully changed.\r\n".encode())
                        else:
                            client.send("550 Failed to change directory.\r\n".encode())
                            
                    elif command == "LIST":
                        self._handle_list(client, current_dir, arg)
                        
                    elif command == "RETR":
                        self.log_attack(
                            addr,
                            "FTP_FILE_DOWNLOAD",
                            f"Attempting download: {arg}",
                            "HIGH"
                        )
                        client.send("550 Failed to open file.\r\n".encode())
                        
                    elif command == "STOR":
                        self.log_attack(
                            addr,
                            "FTP_FILE_UPLOAD",
                            f"Attempting upload: {arg}",
                            "HIGH"
                        )
                        client.send("550 Permission denied.\r\n".encode())
                        
                    elif command == "DELE":
                        self.log_attack(addr, "FTP_FILE_DELETE", f"Delete: {arg}", "HIGH")
                        client.send("550 Permission denied.\r\n".encode())
                        
                    elif command == "SIZE":
                        client.send(f"213 {random.randint(1000, 10000000)}\r\n".encode())
                        
                    elif command == "QUIT":
                        client.send("221 Goodbye.\r\n".encode())
                        break
                        
                    else:
                        client.send("502 Command not implemented.\r\n".encode())
                        
                except socket.timeout:
                    break
                except Exception:
                    break
                    
        except Exception as e:
            self.log_attack(addr, "FTP_ERROR", str(e)[:100], "LOW")
        finally:
            try:
                client.close()
            except:
                pass
                
    def _handle_list(self, client: socket.socket, directory: str, arg: str):
        """Handle LIST command with realistic output"""
        files = self.fake_files.get(directory, [])
        
        # Add some hidden files
        if directory == "/home/admin":
            files = files + [".bash_history", ".mysql_history", ".netrc"]
            
        # Generate realistic listing
        listing = ""
        for f in files:
            if f.startswith("."):
                perms = "-rw-------"
            else:
                perms = random.choice(["-rw-r--r--", "-rwxr-xr-x", "-rw-rw-r--"])
            size = random.randint(512, 1048576)
            date = f"{random.randint(1,12):02d} {random.choice(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])} {random.randint(10,30):02d} {random.randint(0,23):02d}:{random.randint(0,59):02d}"
            if "." in f:
                listing += f"{perms} 2 root root {size:>10} {date} {f}\r\n"
            else:
                listing += f"drwxr-xr-x 3 root root {size:>10} {date} {f}/\r\n"
                
        client.send(f"150 Here comes the directory listing.\r\n".encode())
        client.send(listing.encode())
        client.send("226 Directory send OK.\r\n".encode())


class HTTPHoneypot(HoneypotService):
    """HTTP honeypot with realistic web server simulation"""
    
    def __init__(self, port: int = 80):
        super().__init__(ServiceType.HTTP, port)
        self.fake_paths = self._generate_fake_paths()
        
    def _generate_fake_paths(self) -> Dict:
        """Generate realistic fake web paths"""
        return {
            "/": self._generate_html_response("Apache2 Ubuntu Default Page"),
            "/admin": self._generate_html_response("Admin Panel - Login Required", status=200),
            "/admin/login": self._generate_html_response("Login - Access Denied", status=200),
            "/wp-admin": self._generate_html_response("WordPress Login", status=200),
            "/phpmyadmin": self._generate_html_response("phpMyAdmin", status=200),
            "/.env": self._generate_html_response("403 Forbidden", status=403),
            "/config.php": self._generate_html_response("404 Not Found", status=404),
            "/backup.sql": self._generate_html_response("403 Forbidden", status=403),
            "/api": self._generate_json_response({"status": "ok", "version": "1.0"}),
            "/api/v1/users": self._generate_json_response({"users": []}),
            "/robots.txt": self._generate_text_response("""User-agent: *
Disallow: /admin/
Disallow: /private/
Allow: /
"""),
            "/.git/config": self._generate_html_response("403 Forbidden", status=403),
            "/.git/HEAD": self._generate_html_response("403 Forbidden", status=403),
            "/.htaccess": self._generate_text_response("Order deny,allow\nDeny from all"),
        }
        
    def _generate_html_response(self, content: str, status: int = 200) -> bytes:
        """Generate realistic HTML response"""
        status_text = {200: "OK", 403: "Forbidden", 404: "Not Found", 500: "Internal Server Error"}
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{content}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{content}</h1>
        <p>Apache/2.4.41 (Ubuntu) Server at localhost Port 80</p>
    </div>
</body>
</html>"""
        response = f"HTTP/1.1 {status} {status_text.get(status, 'OK')}\r\n"
        response += "Server: Apache/2.4.41 (Ubuntu)\r\n"
        response += f"Content-Length: {len(html)}\r\n"
        response += "Content-Type: text/html\r\n"
        response += "Connection: close\r\n"
        response += "\r\n"
        response += html
        return response.encode()
        
    def _generate_json_response(self, data: dict) -> bytes:
        """Generate JSON response"""
        import json
        content = json.dumps(data)
        response = "HTTP/1.1 200 OK\r\n"
        response += "Server: Apache/2.4.41 (Ubuntu)\r\n"
        response += f"Content-Length: {len(content)}\r\n"
        response += "Content-Type: application/json\r\n"
        response += "Connection: close\r\n"
        response += "\r\n"
        response += content
        return response.encode()
        
    def _generate_text_response(self, content: str) -> bytes:
        """Generate text response"""
        response = "HTTP/1.1 200 OK\r\n"
        response += "Server: Apache/2.4.41 (Ubuntu)\r\n"
        response += f"Content-Length: {len(content)}\r\n"
        response += "Content-Type: text/plain\r\n"
        response += "Connection: close\r\n"
        response += "\r\n"
        response += content
        return response.encode()
        
    def _handle_connection(self, client: socket.socket, addr: tuple):
        """Handle HTTP connection"""
        try:
            client.settimeout(10)
            
            # Read request
            request = b""
            headers_end = b"\r\n\r\n"
            while headers_end not in request:
                chunk = client.recv(4096)
                if not chunk:
                    return
                request += chunk
                
            request_str = request.decode('utf-8', errors='ignore')
            
            # Parse request
            lines = request_str.split('\r\n')
            if not lines:
                return
                
            request_line = lines[0].split()
            if len(request_line) < 2:
                return
                
            method = request_line[0]
            path = request_line[1]
            
            # Log the request
            self.log_attack(
                addr,
                f"HTTP_{method}",
                f"{method} {path}",
                "MEDIUM"
            )
            
            # Check for common attack patterns
            attack_indicators = [
                ("SQL_INJECTION", ["'", "UNION", "SELECT", "DROP TABLE", "--", ";--", "1=1"]),
                ("XSS", ["<script>", "javascript:", "onerror=", "onload="]),
                ("PATH_TRAVERSAL", ["../", "..\\", "/etc/passwd", "boot.ini"]),
                ("COMMAND_INJECTION", [";ls", ";cat", "|ls", "|nc", "`", "$("]),
                ("WORDPRESS_SCAN", ["/wp-login", "/wp-admin", "/wp-config.php"]),
                ("DIRBUST", ["/admin", "/phpmyadmin", "/backup", "/.git"]),
                ("CMS_SCAN", ["/joomla", "/drupal", "/magento"]),
                ("API_SCAN", ["/api/", "/v1/", "/v2/"]),
            ]
            
            for technique, patterns in attack_indicators:
                for pattern in patterns:
                    if pattern.lower() in path.lower():
                        self.log_attack(
                            addr,
                            technique,
                            f"{method} {path}",
                            "HIGH"
                        )
                        break
                        
            # Extract headers
            headers = {}
            for line in lines[1:]:
                if ": " in line:
                    key, value = line.split(": ", 1)
                    headers[key.lower()] = value
                    
            # Log interesting headers
            if "user-agent" in headers:
                self.log_attack(addr, "HTTP_USER_AGENT", headers["user-agent"], "LOW")
            if "authorization" in headers:
                self.log_attack(addr, "HTTP_AUTH_HEADER", "Base64 credential attempt", "HIGH")
                
            # Check for POST data
            if method == "POST":
                body = request.split(b"\r\n\r\n")[1] if b"\r\n\r\n" in request else b""
                if body:
                    self.log_attack(addr, "HTTP_POST_DATA", body[:200].decode('utf-8', errors='ignore'), "MEDIUM")
                    
            # Send appropriate response
            response = self.fake_paths.get(path)
            if not response:
                # 404 for unknown paths but log the attempt
                self.log_attack(addr, "HTTP_404", f"Unknown path: {path}", "LOW")
                response = self._generate_html_response("404 Not Found", status=404)
                
            client.send(response)
            
        except socket.timeout:
            pass
        except Exception as e:
            self.log_attack(addr, "HTTP_ERROR", str(e)[:100], "LOW")
        finally:
            try:
                client.close()
            except:
                pass


class SMBHoneypot(HoneypotService):
    """SMB honeypot - simulates Windows file shares"""
    
    def __init__(self, port: int = 445):
        super().__init__(ServiceType.SMB, port)
        self.fake_shares = self._generate_fake_shares()
        self.ntlm_auth_attempts = []
        
    def _generate_fake_shares(self) -> Dict:
        """Generate realistic fake SMB shares"""
        return {
            "C$": {"path": "C:\\", "type": "Disk", "comment": "Default share"},
            "ADMIN$": {"path": "C:\\Windows", "type": "Disk", "comment": "Admin share"},
            "IPC$": {"path": "", "type": "IPC", "comment": "Remote IPC"},
            "NETLOGON": {"path": "C:\\Windows\\SYSVOL\\domain\\scripts", "type": "Disk", "comment": "Logon server share"},
            "SYSVOL": {"path": "C:\\Windows\\SYSVOL", "type": "Disk", "comment": "Logon server share"},
            "SharedDocs": {"path": "C:\\Users\\Public\\Documents", "type": "Disk", "comment": "Shared Documents"},
            "Backups": {"path": "D:\\Backups", "type": "Disk", "comment": "Backup storage"},
            "Documents": {"path": "C:\\Users\\Administrator\\Documents", "type": "Disk", "comment": "Admin documents"},
            "Finance": {"path": "E:\\Finance", "type": "Disk", "comment": "Finance department"},
            "IT": {"path": "E:\\IT", "type": "Disk", "comment": "IT department"},
        }
        
    def _handle_connection(self, client: socket.socket, addr: tuple):
        """Handle SMB connection"""
        try:
            client.settimeout(30)
            
            self.log_attack(addr, "SMB_CONNECTION", "New SMB connection", "LOW")
            
            # SMB2/3 negotiate protocol
            negotiate_request = client.recv(1024)
            if not negotiate_request:
                return
                
            # Log the negotiation attempt
            self.log_attack(
                addr,
                "SMB_NEGOTIATE",
                f"Protocol negotiation: {negotiate_request[:50].hex()}",
                "LOW"
            )
            
            # Send SMB2 negotiate response
            negotiate_response = self._build_negotiate_response()
            client.send(negotiate_response)
            
            # Session setup (NTLM auth capture)
            try:
                session_setup = client.recv(4096)
                if session_setup:
                    self._parse_ntlm_auth(client, addr, session_setup)
            except socket.timeout:
                pass
                
            # Handle SMB commands
            for _ in range(random.randint(2, 5)):
                try:
                    cmd = client.recv(4096)
                    if not cmd:
                        break
                        
                    # Detect SMB command type
                    if b"TreeConnect" in cmd or b"\\" in cmd:
                        self._handle_tree_connect(client, addr, cmd)
                    elif b"Create" in cmd:
                        self._handle_file_create(client, addr, cmd)
                    elif b"Read" in cmd:
                        self.log_attack(addr, "SMB_FILE_READ", "File read attempt", "MEDIUM")
                        self._send_error_response(client, 0xC000000D)
                    elif b"Write" in cmd:
                        self.log_attack(addr, "SMB_FILE_WRITE", "File write attempt", "HIGH")
                        self._send_error_response(client, 0xC000000D)
                    else:
                        self.log_attack(
                            addr,
                            "SMB_COMMAND",
                            f"SMB command: {cmd[:32].hex()}",
                            "LOW"
                        )
                        
                except socket.timeout:
                    break
                    
        except Exception as e:
            self.log_attack(addr, "SMB_ERROR", str(e)[:100], "LOW")
        finally:
            try:
                client.close()
            except:
                pass
                
    def _build_negotiate_response(self) -> bytes:
        """Build SMB2 negotiate response"""
        dialect_map = {
            0x0202: "SMB 2.0.2",
            0x0210: "SMB 2.1",
            0x0300: "SMB 3.0",
            0x0302: "SMB 3.0.2",
            0x0310: "SMB 3.1.1",
        }
        dialect = 0x0310
        
        response = bytes([
            0x40, 0x00,
            0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
        ])
        response += bytes([
            0x01, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
        ])
        response += bytes([dialect & 0xFF, (dialect >> 8) & 0xFF, 0x00, 0x00])
        response += bytes([0x0F, 0x00, 0x00, 0x00])
        response += bytes([0x00, 0x00, 0x00, 0x00])
        response += bytes([0x00, 0x00, 0x00, 0x00])
        response += bytes([0x00, 0x00, 0x00, 0x00])
        response += bytes([
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
        ])
        response += bytes([
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
        ])
        response += bytes([
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
        ])
        response += bytes([0x00, 0x00, 0x00, 0x00])
        response += bytes([
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
        ])
        response += bytes([
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
        ])
        response += bytes([
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
        ])
        response += bytes([
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
        ])
        response += bytes([
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
        ])
        
        return response
        
    def _parse_ntlm_auth(self, client: socket.socket, addr: tuple, data: bytes):
        """Parse NTLM authentication attempts"""
        if b"NTLMSSP" in data:
            if b"NTLM" in data:
                self.log_attack(addr, "SMB_NTLM_AUTH", "NTLM authentication attempt", "HIGH")
                
        if b"Administrator" in data or b"admin" in data.lower():
            self.log_attack(addr, "SMB_USER_ENUM", "Administrator/Admin user attempt", "HIGH")
            
    def _handle_tree_connect(self, client: socket.socket, addr: tuple, data: bytes):
        """Handle tree connect request"""
        for share_name in self.fake_shares:
            if share_name.encode() in data:
                self.log_attack(
                    addr,
                    "SMB_TREE_CONNECT",
                    f"Connecting to share: {share_name}",
                    "MEDIUM"
                )
                
    def _handle_file_create(self, client: socket.socket, addr: tuple, data: bytes):
        """Handle file create request"""
        sensitive_files = [
            b"passwd", b"sam", b"system", b"backup",
            b"secret", b"credential", b".kdbx", b".key"
        ]
        for sensitive in sensitive_files:
            if sensitive in data.lower():
                self.log_attack(
                    addr,
                    "SMB_SENSITIVE_ACCESS",
                    f"Accessing sensitive file",
                    "CRITICAL"
                )
                return
        self.log_attack(addr, "SMB_FILE_CREATE", "File create attempt", "MEDIUM")
        
    def _send_error_response(self, client: socket.socket, error_code: int):
        """Send SMB error response"""
        response = bytes([
            0x40, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x05, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
        ])
        response += error_code.to_bytes(4, 'little')
        try:
            client.send(response)
        except Exception:
            pass


class MySQLHoneypot(HoneypotService):
    """MySQL honeypot - captures authentication attempts"""
    
    def __init__(self, port: int = 3306):
        super().__init__(ServiceType.MYSQL, port)
        self.fake_databases = self._generate_fake_databases()
        
    def _generate_fake_databases(self) -> Dict:
        """Generate realistic fake database structure"""
        return {
            "information_schema": {
                "tables": ["CHARACTER_SETS", "COLLATIONS", "COLUMNS", "TABLES", "USER_PRIVILEGES"],
            },
            "mysql": {
                "tables": ["user", "db", "host", "func", "plugin"],
                "users": ["root", "debian-sys-maint", "mysql.session", "mysql.sys"],
            },
            "wordpress_db": {
                "tables": ["wp_users", "wp_posts", "wp_comments", "wp_options", "wp_usermeta"],
                "users": ["admin", "editor", "author"],
            },
            "app_production": {
                "tables": ["users", "sessions", "products", "orders", "payments"],
                "users": ["app_user", "readonly"],
            },
            "sys": {
                "tables": ["sys_config", "host_summary", "innodb_lock_waits"],
            },
        }
        
    def _handle_connection(self, client: socket.socket, addr: tuple):
        """Handle MySQL connection"""
        try:
            client.settimeout(30)
            
            self.log_attack(addr, "MYSQL_CONNECTION", "New MySQL connection", "LOW")
            
            handshake_packet = self._build_handshake()
            client.send(handshake_packet)
            
            while True:
                try:
                    packet = client.recv(8192)
                    if not packet:
                        break
                        
                    packet_type = packet[4] if len(packet) > 4 else 0
                    
                    if packet_type == 0x01:
                        self._handle_auth_packet(client, addr, packet)
                    elif packet_type == 0x03:
                        self._handle_query(client, addr, packet)
                    else:
                        self.log_attack(
                            addr,
                            "MYSQL_PACKET",
                            f"Packet type: {packet_type}",
                            "LOW"
                        )
                        
                except socket.timeout:
                    break
                    
        except Exception as e:
            self.log_attack(addr, "MYSQL_ERROR", str(e)[:100], "LOW")
        finally:
            try:
                client.close()
            except:
                pass
                
    def _build_handshake(self) -> bytes:
        """Build MySQL handshake packet"""
        protocol_version = 10
        server_version = "5.7.36-0ubuntu0.18.04.1"
        connection_id = random.randint(1, 1000)
        auth_plugin_data = os.urandom(20)
        filler = bytes([0] * 13)
        capability_flags = 0x00000fff
        charset = 33
        status_flags = 0x0002
        
        packet = bytes([protocol_version])
        packet += server_version.encode() + b'\x00'
        packet += bytes(connection_id & 0xff)
        packet += auth_plugin_data[:8]
        packet += b'\x00'
        packet += bytes([capability_flags & 0xff, (capability_flags >> 8) & 0xff])
        packet += bytes([charset])
        packet += bytes([status_flags & 0xff, (status_flags >> 8) & 0xff])
        packet += bytes([0x0f, 0x00, 0x00, 0x00])
        packet += auth_plugin_data[8:] + b'\x00'
        
        length = len(packet)
        header = bytes([length & 0xff, (length >> 8) & 0xff, (length >> 16) & 0xff, 0x01])
        
        return header + packet
        
    def _handle_auth_packet(self, client: socket.socket, addr: tuple, packet: bytes):
        """Handle authentication packet"""
        if len(packet) < 36:
            return
            
        username_start = 36
        username_end = packet.find(b'\x00', username_start)
        if username_end > 0:
            username = packet[username_start:username_end].decode('utf-8', errors='ignore')
            
            self.log_attack(
                addr,
                "MYSQL_AUTH_ATTEMPT",
                f"User: {username}",
                "HIGH"
            )
            
            auth_response_start = username_end + 1
            if auth_response_start < len(packet):
                auth_response = packet[auth_response_start:]
                if len(auth_response) > 0:
                    self.log_attack(
                        addr,
                        "MYSQL_AUTH_RESPONSE",
                        f"Auth response length: {len(auth_response)} bytes",
                        "HIGH"
                    )
                    
                    if len(auth_response) == 20:
                        self.log_attack(addr, "MYSQL_SHA256_AUTH", "SHA256 authentication", "MEDIUM")
                    elif len(auth_response) > 0 and len(auth_response) < 20:
                        self.log_attack(addr, "MYSQL_OLD_AUTH", "Old MySQL authentication", "MEDIUM")
                        
        response = bytes([0x00, 0x00, 0x00, 0x02])
        try:
            client.send(response)
        except:
            pass
            
    def _handle_query(self, client: socket.socket, addr: tuple, packet: bytes):
        """Handle SQL query"""
        query_start = 5
        if len(packet) > query_start:
            query = packet[query_start:].decode('utf-8', errors='ignore')
            
            attack_indicators = [
                ("SQL_INJECTION", ["'", "UNION", "SELECT", "DROP", "INSERT", "--", ";--"]),
                ("SQL_ENUM", ["SHOW TABLES", "SHOW DATABASES", "SHOW COLUMNS", "INFORMATION_SCHEMA"]),
                ("SQL_DUMP", ["INTO OUTFILE", "INTO DUMPFILE", "LOAD_FILE"]),
                ("SQL_ADMIN", ["GRANT", "REVOKE", "CREATE USER", "FLUSH PRIVILEGES"]),
            ]
            
            for technique, patterns in attack_indicators:
                for pattern in patterns:
                    if pattern.upper() in query.upper():
                        self.log_attack(addr, technique, query[:100], "HIGH")
                        break
            else:
                self.log_attack(addr, "MYSQL_QUERY", query[:100], "MEDIUM")
                
            self._send_query_response(client)
            
    def _send_query_response(self, client: socket.socket):
        """Send mock query response"""
        error_packet = bytes([
            0x4a, 0x00, 0x00, 0x01,
            0xff, 0x15, 0x04, 0x00,
        ])
        error_msg = "Table 'fake_table' doesn't exist"
        error_packet += bytes([len(error_msg)])
        error_packet += b"23000"
        error_packet += error_msg.encode() + b'\x00'
        
        ok_packet = bytes([0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00])
        
        try:
            client.send(ok_packet)
        except:
            pass


class RDPHoneypot(HoneypotService):
    """RDP honeypot - captures RDP connection attempts"""
    
    def __init__(self, port: int = 3389):
        super().__init__(ServiceType.RDP, port)
        self.connection_sequence = []
        
    def _handle_connection(self, client: socket.socket, addr: tuple):
        """Handle RDP connection"""
        try:
            client.settimeout(30)
            
            self.log_attack(addr, "RDP_CONNECTION", "New RDP connection attempt", "LOW")
            
            x224_connect_request = client.recv(1024)
            if not x224_connect_request:
                return
                
            if len(x224_connect_request) >= 11:
                self.log_attack(
                    addr,
                    "RDP_X224_CONNECT",
                    f"X.224 connection request: {x224_connect_request[:20].hex()}",
                    "LOW"
                )
                
                cookie_present = b"Cookie: mstshash="
                if cookie_present in x224_connect_request:
                    cookie_start = x224_connect_request.index(cookie_present) + len(cookie_present)
                    cookie_end = x224_connect_request.find(b'\r\n', cookie_start)
                    if cookie_end > cookie_start:
                        username = x224_connect_request[cookie_start:cookie_end].decode('utf-8', errors='ignore')
                        self.log_attack(
                            addr,
                            "RDP_USER_ENUM",
                            f"Username attempted: {username}",
                            "HIGH"
                        )
                        
            x224_response = bytes([
                0x03, 0x00, 0x00, 0x0b,
                0x06, 0xd0, 0x00, 0x00,
                0x12, 0x34, 0x00,
            ])
            
            try:
                client.send(x224_response)
            except:
                pass
            
            for _ in range(10):
                try:
                    data = client.recv(4096)
                    if not data:
                        break
                        
                    if b"RDP" in data or b"mstshash" in data:
                        self.log_attack(addr, "RDP_COOKIE", "RDP cookie present", "MEDIUM")
                    elif b"\x03\x00" in data[:2]:
                        self.log_attack(addr, "RDP_TPKT", "RDP TPKT layer", "LOW")
                    elif len(data) > 100:
                        self.log_attack(addr, "RDP_DATA", f"RDP data: {len(data)} bytes", "LOW")
                    else:
                        self.log_attack(addr, "RDP_PROTOCOL", f"Protocol data: {data[:32].hex()}", "LOW")
                        
                except socket.timeout:
                    break
                    
        except Exception as e:
            self.log_attack(addr, "RDP_ERROR", str(e)[:100], "LOW")
        finally:
            try:
                client.close()
            except:
                pass


class TelnetHoneypot(HoneypotService):
    """Telnet honeypot with fake system interaction"""
    
    def __init__(self, port: int = 23):
        super().__init__(ServiceType.TELNET, port)
        self.fake_system = self._generate_fake_system()
        
    def _generate_fake_system(self) -> Dict:
        """Generate fake system information"""
        return {
            "hostname": random.choice(["server1", "web-prod-01", "ubuntu-srv", "debian-box", "linux-server"]),
            "os": random.choice(["Ubuntu 22.04.1 LTS", "Debian GNU/Linux 11", "CentOS Linux 8"]),
            "kernel": f"5.{random.randint(4,15)}.{random.randint(0,50)}-amd64",
            "users": ["root", "admin", "ubuntu", "mysql", "www-data", "backup"],
        }
        
    def _handle_connection(self, client: socket.socket, addr: tuple):
        """Handle Telnet connection"""
        try:
            client.settimeout(120)
            
            self.log_attack(addr, "TELNET_CONNECTION", "New telnet connection", "LOW")
            
            # Send login prompt
            sys = self.fake_system
            login_banner = f"""
{self.theme.CASTLE_ART}

{self.theme.HEADER}

{self.theme.MOTTOES[random.randint(0, len(self.theme.MOTTOES)-1)]}

{self.theme.CASTLE_ART}

{self.theme.CASTLE_ART}

{sys['hostname']} {sys['os']} {sys['kernel']}
{self.theme.HEADER}

{self.theme.CASTLE_ART}

{self.theme.CASTLE_ART}

{sys['hostname']} login: """
            
            client.send(login_banner.encode())
            
            authenticated = False
            current_user = None
            attempts = 0
            
            while attempts < 5:
                try:
                    # Read username
                    client.send(b"")
                    username = b""
                    while True:
                        char = client.recv(1)
                        if not char:
                            return
                        if char == b'\r' or char == b'\n':
                            break
                        if char == b'\x03':  # Ctrl+C
                            return
                        username += char
                        
                    username = username.decode('utf-8', errors='ignore').strip()
                    
                    self.log_attack(
                        addr,
                        "TELNET_USER_ENUM",
                        f"Username attempt: {username}",
                        "MEDIUM"
                    )
                    
                    client.send(b"\r\nPassword: ")
                    
                    # Read password
                    password = b""
                    while True:
                        char = client.recv(1)
                        if not char:
                            return
                        if char == b'\r' or char == b'\n':
                            break
                        if char == b'\x03':
                            return
                        password += char
                        
                    password_str = password.decode('utf-8', errors='ignore')
                    
                    self.log_attack(
                        addr,
                        "TELNET_AUTH_ATTEMPT",
                        f"Login: {username} / {password_str}",
                        "HIGH"
                    )
                    
                    attempts += 1
                    
                    # Simulate login (always fail eventually)
                    if random.random() < 0.15:
                        authenticated = True
                        current_user = username
                        client.send(b"\r\nWelcome to Ubuntu 22.04.1 LTS\r\n")
                        break
                    else:
                        client.send(b"\r\nLogin incorrect\r\n")
                        client.send(f"{sys['hostname']} login: ".encode())
                        
                except socket.timeout:
                    break
                except Exception:
                    break
                    
            # Simulate shell interaction if "authenticated"
            if authenticated:
                self._simulate_shell(client, current_user, sys, addr)
                
        except Exception as e:
            self.log_attack(addr, "TELNET_ERROR", str(e)[:100], "LOW")
        finally:
            try:
                client.close()
            except:
                pass
                
    def _simulate_shell(self, client: socket.socket, user: str, sys: Dict, addr: tuple):
        """Simulate realistic shell interaction"""
        cwd = f"/home/{user}"
        
        commands_responses = {
            "ls": f"""desktop  documents  downloads  music  pictures  public_html  videos
$ ls -la
total 48
drwxr-xr-x 5 {user} {user} 4096 Apr 10 10:30 .
drwxr-xr-x 3 root root 4096 Apr 10 09:00 ..
-rw-r--r-- 1 {user} {user}  220 Apr 10 09:00 .bashrc
-rw------- 1 {user} {user} 8192 Apr 10 10:30 .bash_history
drwx------ 2 {user} {user} 4096 Apr 10 09:00 .ssh
drwxr-xr-x 3 {user} {user} 4096 Apr 10 10:00 documents
""",
            "pwd": f"{cwd}\r\n",
            "whoami": f"{user}\r\n",
            "uname": "Linux {hostname} 5.15.0-56-generic #62-Ubuntu SMP Tue Nov 22 19:54:14 UTC 2022 x86_64 x86_64 x86_64 GNU/Linux\r\n",
            "uname -a": "Linux {hostname} 5.15.0-56-generic #62-Ubuntu SMP Tue Nov 22 19:54:14 UTC 2022 x86_64 x86_64 x86_64 GNU/Linux\r\n",
            "id": f"uid=1000({user}) gid=1000({user}) groups=1000({user}),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev)\r\n",
            "cat /etc/passwd": f"""root:x:0:0:root:/root:/bin/bash
{user}:x:1000:1000:{user},,,:/home/{user}:/bin/bash
mysql:x:27:27:MySQL Server,,,:/var/lib/mysql:/bin/false
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
backup:x:34:34:Backup files,,,:/backup:/bin/bash
""",
            "env": f"""SHELL=/bin/bash
SESSION_MANAGER=local/{hostname}:@/org/freedesktop/display-manager/auto-logout-session,unix:thread-name:/org/freedesktop/display-manager/org.gnome.DisplayManager
USER={user}
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin
HOME=/home/{user}
LOGNAME={user}
""",
            "df -h": """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       100G   45G   55G  45% /
tmpfs           7.8G     0  7.8G   0% /dev/shm
/dev/sdb1       500G   200G   300G  40% /backup
""",
            "ps aux": f"""USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.1  1234  5678 ?        Ss    ?   0:05 /sbin/init
{user}     1234  0.1  0.5  9876  4321 pts/0    Ss    ?   0:01 -bash
{user}     5678  0.0  0.1  2345  1234 pts/0    R+    ?   0:00 ps aux
""",
        }
        
        while True:
            try:
                client.send(f"{user}@{sys['hostname']}:{cwd}$ ".encode())
                
                cmd = b""
                while True:
                    char = client.recv(1)
                    if not char:
                        return
                    if char == b'\r' or char == b'\n':
                        break
                    if char == b'\x03':
                        return
                    if char == b'\x7f':  # Backspace
                        if cmd:
                            cmd = cmd[:-1]
                        continue
                    cmd += char
                    
                cmd_str = cmd.decode('utf-8', errors='ignore').strip()
                
                if not cmd_str:
                    continue
                    
                self.log_attack(addr, "TELNET_COMMAND", cmd_str, "MEDIUM")
                
                # Check for dangerous commands
                dangerous = {
                    "SCANNER": ["nmap", "nikto", "dirb", "gobuster", "sqlmap"],
                    "EXPLOIT": ["msfconsole", "searchsploit", "metasploit"],
                    "DOWNLOAD": ["wget", "curl", "nc", "netcat"],
                    "REVERSE": ["bash -i", "/dev/tcp", "nc -e"],
                    "ENUM": ["enum4linux", "smbclient", "showmount"],
                }
                
                for technique, cmds in dangerous.items():
                    for dangerous_cmd in cmds:
                        if dangerous_cmd in cmd_str.lower():
                            self.log_attack(addr, technique, cmd_str, "HIGH")
                            
                # Provide response
                if cmd_str in commands_responses:
                    response = commands_responses[cmd_str].format(hostname=sys['hostname'], user=user)
                elif cmd_str.startswith("ls "):
                    response = f"{cmd_str}: directory listing\r\n"
                elif cmd_str.startswith("cd "):
                    new_dir = cmd_str[3:].strip()
                    if new_dir == "..":
                        cwd = "/home"
                    else:
                        cwd = f"{cwd}/{new_dir}"
                    response = ""
                elif cmd_str in ["exit", "logout"]:
                    client.send(b"logout\r\n")
                    return
                elif cmd_str == "help":
                    response = """Available commands: ls, pwd, cd, cat, uname, id, env, df, ps, exit
"""
                else:
                    response = f"-bash: {cmd_str.split()[0]}: command not found\r\n"
                    
                client.send(response.encode())
                
            except socket.timeout:
                break
            except Exception:
                break


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Blood-Web Honeypot - Realistic pentesting training tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 blood-web.py                         # Run on non-privileged ports
  sudo python3 blood-web.py                     # Run on privileged ports (22,21,80,23)
  python3 blood-web.py --custom-ports          # Choose custom ports
  python3 blood-web.py --log-dir ./logs        # Custom log location
        """
    )
    
    parser.add_argument('--ssh', action='store_true', default=True, help='Enable SSH honeypot')
    parser.add_argument('--no-ssh', action='store_true', help='Disable SSH honeypot')
    parser.add_argument('--ftp', action='store_true', default=True, help='Enable FTP honeypot')
    parser.add_argument('--http', action='store_true', default=True, help='Enable HTTP honeypot')
    parser.add_argument('--telnet', action='store_true', default=True, help='Enable Telnet honeypot')
    parser.add_argument('--smb', action='store_true', help='Enable SMB honeypot')
    parser.add_argument('--mysql', action='store_true', help='Enable MySQL honeypot')
    parser.add_argument('--rdp', action='store_true', help='Enable RDP honeypot')
    parser.add_argument('--web-monitor', action='store_true', help='Start web monitoring dashboard')
    parser.add_argument('--monitor-port', type=int, default=8081, help='Dashboard port (default: 8081)')
    parser.add_argument('--custom-ports', nargs=7, type=int, metavar=('SSH', 'FTP', 'HTTP', 'TELNET', 'SMB', 'MYSQL', 'RDP'), 
                        help='Custom ports: SSH FTP HTTP TELNET SMB MYSQL RDP')
    parser.add_argument('--log-dir', default='logs', help='Log directory')
    parser.add_argument('--version', action='version', version='Blood-Web Honeypot v1.0')
    
    args = parser.parse_args()
    
    # Initialize honeypot
    config = {
        'log_dir': args.log_dir,
    }
    honeypot = BloodWebHoneypot(config)
    
    # Default ports (non-privileged - work without sudo)
    # Privileged ports: 22, 21, 80, 23, 445, 3306, 3389 (require sudo)
    # Non-privileged: 2222, 2121, 8080, 2323, 4445, 33306, 33890
    default_ports = [2222, 2121, 8080, 2323, 4445, 33306, 33890]
    ports = list(args.custom_ports) if args.custom_ports else default_ports
    
    # Check if using privileged ports
    privileged = [p for p in ports if p < 1024]
    if privileged:
        print(f"\n\033[93m[!] Using privileged ports: {privileged}\033[0m")
        print(f"\033[93m[!] You may need to run with: sudo python3 blood-web.py\033[0m\n")
    
    if args.ssh and not args.no_ssh:
        honeypot.register_service(SSHHoneypot(port=ports[0]))
        
    if args.ftp:
        honeypot.register_service(FTPHoneypot(port=ports[1]))
        
    if args.http:
        honeypot.register_service(HTTPHoneypot(port=ports[2]))
        
    if args.telnet:
        honeypot.register_service(TelnetHoneypot(port=ports[3]))
        
    if args.smb:
        honeypot.register_service(SMBHoneypot(port=ports[4]))
        
    if args.mysql:
        honeypot.register_service(MySQLHoneypot(port=ports[5]))
        
    if args.rdp:
        honeypot.register_service(RDPHoneypot(port=ports[6]))
    
    # Start web monitor if requested
    if args.web_monitor:
        import threading
        from web_monitor import MonitoringServer
        monitor = MonitoringServer(port=args.monitor_port, log_dir=args.log_dir)
        monitor_thread = threading.Thread(target=monitor.start, daemon=True)
        monitor_thread.start()
        print(f"\033[92m[+]\033[0m Web dashboard available at http://localhost:{args.monitor_port}")
        
    # Start
    honeypot.start()


if __name__ == "__main__":
    main()
