#!/usr/bin/env python3
"""
Setup script for Subdomain Enumerator Tool
"""

import os
import sys
import subprocess
import urllib.request

def install_requirements():
    """Install required Python packages"""
    print("Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error installing dependencies: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    directories = [
        "sources",
        "utils", 
        "wordlists",
        "results"
    ]
    
    print("Creating directories...")
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def create_init_files():
    """Create __init__.py files for Python modules"""
    init_files = [
        "sources/__init__.py",
        "utils/__init__.py"
    ]
    
    print("Creating module files...")
    for init_file in init_files:
        with open(init_file, 'w') as f:
            f.write('# Module initialization file\n')
        print(f"✓ Created: {init_file}")

def download_wordlists():
    """Download default wordlists from SecLists"""
    wordlists = [
        {
            "name": "subdomains-top1million-5000.txt",
            "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt"
        },
        {
            "name": "subdomains-top1million-20000.txt", 
            "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-20000.txt"
        },
        {
            "name": "bitquark-subdomains-top100000.txt",
            "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/bitquark-subdomains-top100000.txt"
        }
    ]
    
    print("Downloading wordlists...")
    for wordlist in wordlists:
        file_path = os.path.join("wordlists", wordlist["name"])
        
        if os.path.exists(file_path):
            print(f"✓ {wordlist['name']} already exists")
            continue
            
        try:
            print(f"  Downloading {wordlist['name']}...")
            urllib.request.urlretrieve(wordlist["url"], file_path)
            print(f"✓ Downloaded: {wordlist['name']}")
        except Exception as e:
            print(f"✗ Failed to download {wordlist['name']}: {e}")

def create_example_config():
    """Create example configuration file"""
    config_content = """# Subdomain Enumerator Configuration
# Copy this to config.py and modify as needed

# DNS Servers (in order of preference)
DNS_SERVERS = [
    '8.8.8.8',      # Google
    '8.8.4.4',      # Google
    '1.1.1.1',      # Cloudflare
    '1.0.0.1',      # Cloudflare
    '208.67.222.222', # OpenDNS
    '208.67.220.220'  # OpenDNS
]

# Default timeout for HTTP requests (seconds)
HTTP_TIMEOUT = 10

# Default timeout for DNS requests (seconds)
DNS_TIMEOUT = 5

# Default number of threads
DEFAULT_THREADS = 50

# Maximum number of threads
MAX_THREADS = 200

# Default wordlist path
DEFAULT_WORDLIST = "wordlists/subdomains-top1million-5000.txt"

# API Keys (optional - add your own)
VIRUSTOTAL_API_KEY = None
SHODAN_API_KEY = None
CENSYS_API_ID = None
CENSYS_API_SECRET = None

# Output settings
DEFAULT_OUTPUT_DIR = "results"
SAVE_HTML_REPORT = True
SAVE_CSV_REPORT = True
SAVE_JSON_REPORT = True
"""
    
    config_file = "config_example.py"
    with open(config_file, 'w') as f:
        f.write(config_content)
    print(f"✓ Created example configuration: {config_file}")

def create_run_script():
    """Create convenience run script"""
    run_script_content = """#!/bin/bash
# Convenience script to run subdomain enumeration

# Check if domain argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <domain> [additional_args]"
    echo "Example: $0 example.com"
    echo "Example: $0 example.com -t 100 --skip-passive"
    exit 1
fi

# Run the subdomain enumerator
python3 main.py "$@"
"""
    
    run_script = "run.sh"
    with open(run_script, 'w') as f:
        f.write(run_script_content)
    
    # Make script executable on Unix systems
    if os.name != 'nt':
        os.chmod(run_script, 0o755)
    
    print(f"✓ Created run script: {run_script}")

def main():
    """Main setup function"""
    print("="*60)
    print("SUBDOMAIN ENUMERATOR TOOL SETUP")
    print("="*60)
    
    # Create directories
    create_directories()
    
    # Create module files
    create_init_files()
    
    # Install dependencies
    if not install_requirements():
        print("Setup failed due to dependency installation error")
        return False
    
    # Download wordlists
    download_wordlists()
    
    # Create configuration
    create_example_config()
    
    # Create run script
    create_run_script()
    
    print("\n" + "="*60)
    print("SETUP COMPLETE!")
    print("="*60)
    print("To use the tool:")
    print("  python3 main.py -d example.com")
    print("  ./run.sh example.com")
    print("")
    print("For help:")
    print("  python3 main.py --help")
    print("")
    print("Configuration:")
    print("  Edit config_example.py and save as config.py")
    print("="*60)
    
    return True

if __name__ == "__main__":
    main()