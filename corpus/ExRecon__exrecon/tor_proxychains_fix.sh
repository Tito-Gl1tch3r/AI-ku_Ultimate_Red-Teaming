#!/bin/bash

# ExRecon - TOR + Proxychains Auto Fix & Test Script

LOGFILE="$HOME/tor_proxychains_fix.log"
TORRC="/etc/tor/torrc"
PROXYCHAINS_TEST_URL="https://check.torproject.org"

GREEN="\033[1;32m"
RED="\033[1;31m"
YELLOW="\033[1;33m"
NC="\033[0m"

echo -e "\n[+] Starting TOR & Proxychains auto-check..." | tee -a "$LOGFILE"

# Step 1: Start tor@default or fix config
echo "[*] Attempting to start tor@default.service..." | tee -a "$LOGFILE"
sudo systemctl start tor@default 2>>"$LOGFILE"

if ! systemctl is-active --quiet tor@default; then
    echo -e "${YELLOW}[!] TOR failed to start. Attempting config fix...${NC}" | tee -a "$LOGFILE"
    
    # Backup torrc
    sudo cp "$TORRC" "${TORRC}.bak_$(date +%s)" 2>>"$LOGFILE"

    # Clean duplicate entries and apply defaults
    sudo sed -i "/^ControlPort/d;/^CookieAuthentication/d" "$TORRC"
    echo -e "\nControlPort 9051\nCookieAuthentication 1" | sudo tee -a "$TORRC" > /dev/null

    sudo systemctl restart tor@default 2>>"$LOGFILE"
    sleep 2
fi

# Step 2: Test TOR routing via Proxychains
echo "[*] Testing proxychains with TOR network..." | tee -a "$LOGFILE"
if proxychains curl -s "$PROXYCHAINS_TEST_URL" | grep -q "Congratulations"; then
    echo -e "${GREEN}[+] TOR is working through Proxychains!${NC}" | tee -a "$LOGFILE"
else
    echo -e "${RED}[!] TOR check failed after fix. Please review $LOGFILE.${NC}" | tee -a "$LOGFILE"
fi
