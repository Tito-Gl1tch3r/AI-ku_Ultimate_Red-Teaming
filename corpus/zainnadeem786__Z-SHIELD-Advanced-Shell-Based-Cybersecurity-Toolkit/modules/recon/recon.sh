#!/bin/bash

# Z-SHIELD Recon Module
# Author: ZAIN NADEEM
# Purpose: Aggressive but fast recon for open ports, DNS, and WP detection

# Colors
RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
CYAN="\033[1;36m"
RESET="\033[0m"
BOLD="\033[1m"

# ASCII Table Border
table_line() {
  printf "${CYAN}+--------------------+-------------------------------------------+\n"
}

print_table_row() {
  printf "${CYAN}| %-18s | %-41s |\n" "$1" "$2"
}

# Banner
clear
echo -e "${GREEN}${BOLD}"
figlet -f ANSI_Shadow "Recon Module" | lolcat
echo -e "${CYAN}${BOLD}         Z-SHIELD Exploitation Module${RESET}"
echo -e "${YELLOW}          Developed by ${RESET}${WHITE}ZAIN NADEEM${RESET}"
echo ""

# Ask for input
read -p "$(echo -e ${YELLOW}Enter target domain or IP: ${RESET})" TARGET

echo -e "${CYAN}\n[✓] Starting aggressive port scan (open ports only)...${RESET}"
open_ports=$(nmap -Pn -T4 --open -p- --min-rate=500 "$TARGET" | grep -E '^[0-9]+/tcp' | awk '{print $1, $2, $3}' )

# Output in table format
if [ -n "$open_ports" ]; then
  echo -e "${GREEN}\nOpen Ports Found:${RESET}"
  table_line
  print_table_row "PORT" "STATE & SERVICE"
  table_line
  echo "$open_ports" | while read -r line; do
    port=$(echo "$line" | awk '{print $1}')
    state=$(echo "$line" | awk '{print $2}')
    service=$(echo "$line" | awk '{print $3}')
    print_table_row "$port" "$state $service"
  done
  table_line
else
  echo -e "${RED}No open ports found.${RESET}"
fi

# DNS Enumeration
echo -e "${CYAN}\n[✓] Running DNS Enumeration...${RESET}"
dnsenum_output=$(dnsenum "$TARGET" 2>/dev/null)

echo -e "${GREEN}\nDNS Enumeration Results:${RESET}"
table_line
print_table_row "TYPE" "DATA"
table_line

echo "$dnsenum_output" | grep -E "(A |NS |MX |TXT )" | while read -r line; do
  type=$(echo "$line" | awk '{print $1}')
  data=$(echo "$line" | cut -d' ' -f2-)
  print_table_row "$type" "$data"
done
table_line

# --- WordPress Detection (Improved) ---
echo -e "${CYAN}\n[✓] Checking if target is a WordPress site...${RESET}"
wpscan --url "$TARGET" --no-update --stealthy --ignore-main-redirect --random-user-agent > /tmp/zshield_wp.tmp 2>/dev/null

if grep -q "WordPress" /tmp/zshield_wp.tmp; then
  echo -e "${GREEN}\n[+] WordPress Detected${RESET}"
  table_line

  version=$(grep -i "WordPress version" /tmp/zshield_wp.tmp | head -1 | cut -d':' -f2-)
  if [[ -n "$version" ]]; then
    print_table_row "Version" "$version"
  else
    print_table_row "Version" "Not Detected"
  fi

  theme=$(grep -i "Theme Name:" /tmp/zshield_wp.tmp | head -1 | cut -d':' -f2-)
  if [[ -n "$theme" ]]; then
    print_table_row "Theme" "$theme"
  fi

  grep -i "Plugin Name:" /tmp/zshield_wp.tmp | cut -d':' -f2 | head -5 | while read -r plugin; do
    print_table_row "Plugin" "$plugin"
  done

  table_line
else
  echo -e "${YELLOW}[-] Target is not a WordPress site or WPScan could not detect it.${RESET}"
fi
rm -f /tmp/zshield_wp.tmp

echo -e "${MAGENTA}\n[✓] Recon complete. Stay sharp, stay hidden.${RESET}\n"
