#!/bin/bash
# ============================================
# Start pentesting lab
# ============================================

set -e

echo "[*] Starting pentesting lab..."
echo ""

# Check that VirtualBox is installed
if ! command -v VBoxManage &> /dev/null; then
    echo "[-] VirtualBox not found. Install it first."
    exit 1
fi

# List available VMs
echo "[*] Available VMs:"
VBoxManage list vms | grep -E "Metasploitable|DVWA|OWASP|Windows|Debian"
echo ""

# Function to start VM
start_vm() {
    local vm_name="$1"
    local vm_state
    vm_state=$(VBoxManage showvminfo "$vm_name" --machinereadable 2>/dev/null | grep "VMState=" | cut -d'"' -f2)
    
    if [ "$vm_state" = "running" ]; then
        echo "[+] $vm_name is already running"
    else
        echo "[*] Starting $vm_name..."
        VBoxManage startvm "$vm_name" --type headless 2>/dev/null || echo "[-] Could not start $vm_name"
    fi
}

# Start lab VMs
echo "[*] Starting lab VMs..."
echo ""

# Try to start each VM (ignore if not found)
for vm in "Metasploitable2" "Metasploitable" "DVWA" "OWASP_BWA" "Windows XP" "Windows 7"; do
    VBoxManage showvminfo "$vm" &>/dev/null && start_vm "$vm" &
done

wait

echo ""
echo "[*] Waiting for VMs to be ready..."
sleep 10

echo ""
echo "============================================"
echo "LAB STARTED"
echo "============================================"
echo ""
echo "Verify with: ./verify_lab.sh"
echo ""
echo "Lab IPs:"
echo "  Kali:       192.168.56.100"
echo "  Metasploit: 192.168.56.200"
echo "  DVWA:       http://192.168.56.201"
echo "  OWASP BWA:  http://192.168.56.202"
echo ""
echo "============================================"
