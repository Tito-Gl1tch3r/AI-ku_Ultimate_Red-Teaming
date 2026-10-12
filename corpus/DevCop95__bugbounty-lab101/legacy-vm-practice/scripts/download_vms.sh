#!/bin/bash
# ============================================
# Script to download vulnerable VMs
# ============================================

set -e

DOWNLOAD_DIR="$(dirname "$0")/../vms"
mkdir -p "$DOWNLOAD_DIR"

echo "============================================"
echo "  Vulnerable VM Downloader"
echo "============================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to show menu
show_menu() {
    echo "Select the VMs to download:"
    echo ""
    echo "  1) Metasploitable 2 (Vulnerable Linux) - 1.8GB"
    echo "  2) DVWA (Vulnerable Web) - Docker"
    echo "  3) OWASP BWA (Vulnerable web apps) - 4GB"
    echo "  4) Windows XP (Legacy vulnerable) - 1.5GB"
    echo "  5) All of the above"
    echo "  0) Exit"
    echo ""
}

# Metasploitable 2
download_metasploitable() {
    echo ""
    echo -e "${GREEN}[*] Metasploitable 2${NC}"
    echo "URL: https://sourceforge.net/projects/metasploitable/files/Metasploitable2/metasploitable2-vm-0.0.1.zip"
    echo ""
    echo "Steps:"
    echo "  1. Download the ZIP from the URL above"
    echo "  2. Extract to: $DOWNLOAD_DIR/"
    echo "  3. Import in VirtualBox (File → Import)"
    echo "  4. Configure network: Host-Only Adapter"
    echo "  5. Static IP: 192.168.56.200"
    echo ""
}

# DVWA con Docker
setup_dvwa_docker() {
    echo ""
    echo -e "${GREEN}[*] DVWA with Docker${NC}"
    echo ""
    
    if command -v docker &> /dev/null; then
        echo "Docker detected. Installing DVWA..."
        echo ""
        
        # Pull image
        docker pull vulnerables/web-dvwa
        
        # Run container
        echo "Starting DVWA..."
        docker run --rm -d --name dvwa -p 80:80 vulnerables/web-dvwa
        
        echo ""
        echo -e "${GREEN}[+] DVWA running at: http://localhost${NC}"
        echo "Credentials: admin / password"
        echo ""
        echo "To stop: docker stop dvwa"
    else
        echo -e "${YELLOW}[!] Docker not found${NC}"
        echo ""
        echo "Option 1: Install Docker"
        echo "  sudo apt install docker.io"
        echo "  sudo usermod -aG docker \$USER"
        echo "  newgrp docker"
        echo ""
        echo "Option 2: Download VM"
        echo "  Search for 'DVWA' at: https://www.vulnhub.com/"
    fi
}

# OWASP BWA
download_owasp_bwa() {
    echo ""
    echo -e "${GREEN}[*] OWASP Broken Web Applications${NC}"
    echo "URL: https://sourceforge.net/projects/owaspbwa/files/"
    echo ""
    echo "Steps:"
    echo "  1. Download the ISO/OVA from SourceForge"
    echo "  2. Import in VirtualBox"
    echo "  3. Configure network: Host-Only Adapter"
    echo "  4. Static IP: 192.168.56.202"
    echo ""
}

# Windows XP
download_windows_xp() {
    echo ""
    echo -e "${GREEN}[*] Windows XP${NC}"
    echo "NOTE: You need a Windows XP license"
    echo ""
    echo "Alternative: Use Windows 7 Enterprise trial"
    echo "URL: https://www.microsoft.com/en-us/evalcenter/evaluate-windows-7-enterprise"
    echo ""
    echo "Steps:"
    echo "  1. Download the ISO"
    echo "  2. Create VM in VirtualBox"
    echo "  3. Install Windows"
    echo "  4. Configure network: Host-Only Adapter"
    echo "  5. Static IP: 192.168.56.203"
    echo ""
}

# Main menu
while true; do
    show_menu
    read -p "Select an option: " choice
    
    case $choice in
        1)
            download_metasploitable
            ;;
        2)
            setup_dvwa_docker
            ;;
        3)
            download_owasp_bwa
            ;;
        4)
            download_windows_xp
            ;;
        5)
            download_metasploitable
            setup_dvwa_docker
            download_owasp_bwa
            download_windows_xp
            ;;
        0)
            echo ""
            echo "Good luck with your lab!"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
    clear
done
