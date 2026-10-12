#!/usr/bin/env python3
"""
Logger Module
Provides colored logging functionality
"""

import sys
from datetime import datetime

class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class Logger:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.start_time = datetime.now()
    
    def set_verbose(self, verbose):
        """Set verbose mode"""
        self.verbose = verbose
    
    def _print_with_time(self, message, color="", prefix=""):
        """Print message with timestamp and color"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if prefix:
            print(f"{color}[{timestamp}] {prefix}: {message}{Colors.END}")
        else:
            print(f"{color}[{timestamp}] {message}{Colors.END}")
    
    def info(self, message):
        """Print info message"""
        self._print_with_time(message, Colors.BLUE, "INFO")
    
    def success(self, message):
        """Print success message"""
        self._print_with_time(message, Colors.GREEN, "SUCCESS")
    
    def warning(self, message):
        """Print warning message"""
        self._print_with_time(message, Colors.YELLOW, "WARNING")
    
    def error(self, message):
        """Print error message"""
        self._print_with_time(message, Colors.RED, "ERROR")
    
    def debug(self, message):
        """Print debug message (only in verbose mode)"""
        if self.verbose:
            self._print_with_time(message, Colors.MAGENTA, "DEBUG")
    
    def header(self, message):
        """Print header message"""
        line = "=" * 60
        print(f"\n{Colors.CYAN}{Colors.BOLD}{line}")
        print(f"{message.center(60)}")
        print(f"{line}{Colors.END}\n")
    
    def subheader(self, message):
        """Print subheader message"""
        print(f"\n{Colors.CYAN}{Colors.BOLD}--- {message} ---{Colors.END}")
    
    def progress(self, current, total, message=""):
        """Print progress bar"""
        percentage = (current / total) * 100 if total > 0 else 0
        bar_length = 40
        filled_length = int(bar_length * current // total) if total > 0 else 0
        
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        if message:
            print(f"\r{Colors.BLUE}[{bar}] {percentage:.1f}% - {message}{Colors.END}", end='', flush=True)
        else:
            print(f"\r{Colors.BLUE}[{bar}] {percentage:.1f}%{Colors.END}", end='', flush=True)
    
    def print_banner(self):
        """Print tool banner"""
        banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                    SUBDOMAIN ENUMERATOR                      ║
║                     Reconnaissance Tool                      ║
║                                                              ║
║  Multiple Source Enumeration + Bruteforce + Live Checking   ║
╚══════════════════════════════════════════════════════════════╝
{Colors.END}
"""
        print(banner)
    
    def print_results_summary(self, domain, total_subdomains, live_subdomains, elapsed_time):
        """Print enumeration results summary"""
        success_rate = (live_subdomains / total_subdomains * 100) if total_subdomains > 0 else 0
        
        summary = f"""
{Colors.GREEN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                       ENUMERATION COMPLETE                  ║
╠══════════════════════════════════════════════════════════════╣
║  Target Domain      : {domain:<42} ║
║  Total Subdomains   : {total_subdomains:<42} ║
║  Live Subdomains    : {live_subdomains:<42} ║
║  Success Rate       : {success_rate:.1f}%{' '*(38)}║
║  Execution Time     : {elapsed_time:.2f}s{' '*(35)}║
╚══════════════════════════════════════════════════════════════╝
{Colors.END}
"""
        print(summary)
    
    def print_live_subdomain(self, subdomain, protocols):
        """Print live subdomain discovery"""
        protocol_str = ", ".join([p.upper() for p in protocols])
        print(f"{Colors.GREEN}[+] LIVE: {subdomain} [{protocol_str}]{Colors.END}")
    
    def print_method_result(self, method_name, count):
        """Print enumeration method result"""
        if count > 0:
            print(f"{Colors.GREEN}  ✓ {method_name}: {count} subdomains{Colors.END}")
        else:
            print(f"{Colors.YELLOW}  - {method_name}: 0 subdomains{Colors.END}")
    
    def print_file_saved(self, file_type, file_path):
        """Print file saved message"""
        print(f"{Colors.CYAN}  📁 {file_type}: {file_path}{Colors.END}")
    
    def print_separator(self, char="-", length=60):
        """Print separator line"""
        print(f"{Colors.CYAN}{char * length}{Colors.END}")
    
    def elapsed_time(self):
        """Get elapsed time since logger initialization"""
        return datetime.now() - self.start_time