#!/bin/bash
# ============================================
# Tool Checker - Kali Tool Verifier
# ============================================
# Verify which tools are installed
# and recommend installation of missing ones
# ============================================

# Note: intentionally not using set -e — bash arithmetic ((var++)) returns\n# exit code 1 when the value is 0, which would cause premature abort.

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              KALI TOOL CHECKER v1.0                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Tool categories
declare -A CATEGORIES=(
    [RECON]="nmap masscan zmap dnsrecon theHarvester amass recon-ng whois dig host httpx katana gau nuclei"
    [DNS]="subfinder sublist3r fierce subbrute dnsgen gotator dnsenum dnsmap"
    [WEB]="nikto whatweb gobuster dirb wfuzz ffuf feroxbuster dirsearch sqlmap xsser dalfox wpscan nuclei"
    [ENUM]="enum4linux smbclient smbmap nbtscan ldapsearch rpcclient snmpwalk onesixtyone bloodhound"
    [HTTP]="gobuster ffuf wfuzz feroxbuster dirsearch arjun paramspider x8"
    [SMB]="enum4linux smbclient smbmap crackmapexec netexec smbexec"
    [LDAP]="ldapsearch ldapenum ldeep ldapdomaindump windapsearch"
    [SNMP]="snmpwalk onesixtyone snmp-check snmpenum"
    [BRUTE]="hydra medusa ncrack john hashcat cewl crunch"
    [EXPLOIT]="metasploit searchsploit msfvenom veil shellter scarecrow donut"
    [EXPLOIT_WEB]="sqlmap xsser dalfox xsstrike commix tplmap wpscan cmseek"
    [POST]="crackmapexec impacket evil-winrm chisel responder mimikatz laZagne"
    [PRIVESC]="linpeas winpeas linuxprivchecker beroot"
    [C2]="empire sliver havoc mythic"
    [TUNNEL]="chisel ligolo-ng sshuttle proxychains resocks"
    [EVADE]="veil shellter scarecrow avet donut shikata-ga-nai"
    [AD]="bloodhound sharphound rubeus mimikatz certipy whisker"
    [WIRELESS]="aircrack-ng wifite kismet reaver bully"
    [TRAFFIC]="wireshark tshark tcpdump ettercap mitmproxy"
    [FORENSICS]="volatility autopsy binwalk foremost sleuthkit"
    [REVERSING]="ghidra radare2 strace ltrace objdump"
    [SOCIAL]="set king-phisher gophish"
    [PASSWORD]="ophcrack chntpw mimikatz lazagne"
    [CLOUD]="s3scanner cloud_enum lazys3 bucket_finder"
    [OSINT]="sherlock holehe gasmask spiderfoot"
    [FINGERPRINT]="whatweb wappalyzer webanalyze retirejs"
    [TAKEOVER]="subjack subover canari"
    [SECRETS]="gitleaks trufflehog detect_secrets gitrob"
)

# Colors by status
INSTALLED=0
MISSING=0
TOTAL=0

echo "=== Tool Verification ==="
echo ""

for category in "${!CATEGORIES[@]}"; do
    echo -e "${CYAN}[$category]${NC}"
    
    for tool in ${CATEGORIES[$category]}; do
        ((TOTAL++))
        if command -v "$tool" &>/dev/null; then
            echo -e "  ${GREEN}✓${NC} $tool"
            ((INSTALLED++))
        else
            echo -e "  ${RED}✗${NC} $tool"
            ((MISSING++))
        fi
    done
    echo ""
done

# Summary
echo "═══════════════════════════════════════════════════════════════"
echo -e "Total: ${CYAN}$TOTAL${NC} tools"
echo -e "Installed: ${GREEN}$INSTALLED${NC}"
echo -e "Missing: ${RED}$MISSING${NC}"
echo ""

# Percentage
PERCENT=$((INSTALLED * 100 / TOTAL))
if [ $PERCENT -ge 80 ]; then
    echo -e "${GREEN}Excellent: $PERCENT% of tools installed${NC}"
elif [ $PERCENT -ge 50 ]; then
    echo -e "${YELLOW}Good: $PERCENT% of tools installed${NC}"
else
    echo -e "${RED}Needs improvement: $PERCENT% of tools installed${NC}"
fi

echo ""
echo "=== Missing Tools ==="
echo ""

# Recommend installation
MISSING_TOOLS=""
for category in "${!CATEGORIES[@]}"; do
    for tool in ${CATEGORIES[$category]}; do
        if ! command -v "$tool" &>/dev/null; then
            MISSING_TOOLS="$MISSING_TOOLS $tool"
        fi
    done
done

if [ -n "$MISSING_TOOLS" ]; then
    echo "To install missing tools run:"
    echo ""
    echo -e "${CYAN}sudo apt install$MISSING_TOOLS${NC}"
    echo ""
    echo "Or install by category:"
    echo ""
    echo "  Reconnaissance: sudo apt install amass theharvester recon-ng"
    echo "  Web:             sudo apt install wfuzz ffuf xsser wpscan"
    echo "  Enumeration:     sudo apt install enum4linux smbclient"
    echo "  Brute force:     sudo apt install hydra medusa john hashcat"
    echo "  Exploitation:    sudo apt install metasploit-framework"
    echo "  Post-exploitation: sudo apt install crackmapexec impacket-scripts"
    echo "  Wireless:        sudo apt install wifite reaver bully"
    echo "  Forensics:       sudo apt install autopsy sleuthkit binwalk foremost"
    echo "  Reversing:       sudo apt install ghidra radare2"
else
    echo -e "${GREEN}All tools are installed!${NC}"
fi
