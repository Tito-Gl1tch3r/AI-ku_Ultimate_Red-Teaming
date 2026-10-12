#!/bin/bash
# ============================================
# Check lab status
# ============================================

echo "[*] Checking lab status..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Check connectivity
check_host() {
    local ip="$1"
    local name="$2"
    
    if ping -c 1 -W 1 "$ip" &> /dev/null; then
        echo -e "${GREEN}[+]${NC} $name ($ip) - ONLINE"
        return 0
    else
        echo -e "${RED}[-]${NC} $name ($ip) - OFFLINE"
        return 1
    fi
}

# Check HTTP services
check_web() {
    local url="$1"
    local name="$2"
    
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200\|301\|302"; then
        echo -e "${GREEN}[+]${NC} $name - RESPONDING"
        return 0
    else
        echo -e "${RED}[-]${NC} $name - NOT RESPONDING"
        return 1
    fi
}

echo "============================================"
echo "LAB VERIFICATION"
echo "============================================"
echo ""

# Check hosts
echo "[*] Hosts:"
check_host "192.168.56.100" "Kali Linux"
check_host "192.168.56.200" "Metasploitable"
check_host "192.168.56.201" "DVWA"
check_host "192.168.56.202" "OWASP BWA"
echo ""

# Check web services
echo "[*] Web Services:"
check_web "http://192.168.56.200" "Metasploitable Web"
check_web "http://192.168.56.201" "DVWA"
check_web "http://192.168.56.202" "OWASP BWA"
echo ""

# Check open ports on Metasploitable
echo "[*] Open ports on Metasploitable (192.168.56.200):"
if command -v nmap &> /dev/null; then
    nmap -sT --top-ports 20 192.168.56.200 -oG - 2>/dev/null | grep "open" | awk '{print "    " $2 ": " $3}' | sed 's/\/open//g'
else
    echo "    [!] nmap not found. Install it with: sudo apt install nmap"
fi
echo ""

echo "============================================"
echo "USEFUL COMMANDS"
echo "============================================"
echo ""
echo "  Full scan:         nmap -sV -sC 192.168.56.200"
echo "  Web scan:          nikto -h http://192.168.56.201"
echo "  Dirbusting:          dirb http://192.168.56.201"
echo "  SQL Injection:       sqlmap -u 'http://192.168.56.201/vulnerabilities/sqli/'"
echo ""
echo "============================================"
