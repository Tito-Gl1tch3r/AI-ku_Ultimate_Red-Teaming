#!/bin/bash
# ============================================
# Configure pentesting lab network
# ============================================

set -e

echo "[*] Configuring lab network..."

# Detect VirtualBox
if command -v VBoxManage &> /dev/null; then
    echo "[+] VirtualBox detected"
    
    # Create Host-Only network if it does not exist
    echo "[*] Verifying Host-Only network..."
    HOST_ONLY=$(VBoxManage list hostonlyifs | grep "Name:" | head -1 | awk '{print $2}')
    
    if [ -z "$HOST_ONLY" ]; then
        echo "[*] Creating Host-Only interface..."
        VBoxManage hostonlyif create
        HOST_ONLY=$(VBoxManage list hostonlyifs | grep "Name:" | head -1 | awk '{print $2}')
    fi
    
    echo "[+] Using interface: $HOST_ONLY"
    
    # Configure Host-Only interface IP
    echo "[*] Configuring IP 192.168.56.1 on $HOST_ONLY..."
    VBoxManage hostonlyif ipconfig "$HOST_ONLY" --ip 192.168.56.1 --netmask 255.255.255.0
    
    echo "[+] Network configured successfully"
    
else
    echo "[-] VirtualBox not found"
    echo "    Install VirtualBox or configure the network manually"
fi

echo ""
echo "============================================"
echo "NETWORK CONFIGURATION:"
echo "============================================"
echo ""
echo "  Red:        192.168.56.0/24"
echo "  Gateway:    192.168.56.1 (your machine)"
echo "  Kali:       192.168.56.100"
echo "  Metasploit: 192.168.56.200"
echo "  DVWA:       192.168.56.201"
echo "  OWASP BWA:  192.168.56.202"
echo ""
echo "============================================"
