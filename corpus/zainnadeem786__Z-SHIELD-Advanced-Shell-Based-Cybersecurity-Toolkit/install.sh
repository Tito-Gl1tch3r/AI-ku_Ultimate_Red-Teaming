#!/bin/bash

# Z-SHIELD Installer
# Author: ZAIN NADEEM
# Purpose: Ensure all dependencies for Z-SHIELD are installed and ready

# Colors
RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
CYAN="\033[1;36m"
RESET="\033[0m"
BOLD="\033[1m"

echo -e "${CYAN}${BOLD}╭────────────────────────────────────────────╮"
echo -e "│        Installing Z-SHIELD Toolkit         │"
echo -e "╰────────────────────────────────────────────╯${RESET}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[✘] Please run as root (sudo).${RESET}"
  exit 1
fi

echo -e "${YELLOW}[•] Updating package list...${RESET}"
apt update -y && apt upgrade -y

# Required tools
TOOLS=("nmap" "dnsenum" "wpscan" "net-tools" "clamav" "msfconsole" "tcpdump" "awk" "curl")

echo -e "${YELLOW}[•] Checking and installing dependencies...${RESET}"

for tool in "${TOOLS[@]}"; do
  if ! command -v "$tool" &> /dev/null; then
    echo -e "${CYAN}[+] Installing: $tool...${RESET}"
    if [ "$tool" == "wpscan" ]; then
      gem install wpscan --no-document
    elif [ "$tool" == "msfconsole" ]; then
      echo -e "${YELLOW}[!] Skipping Metasploit install. Please install manually if needed.${RESET}"
    else
      apt install -y "$tool"
    fi
  else
    echo -e "${GREEN}[✓] $tool already installed.${RESET}"
  fi
done

# Freshclam update
if command -v freshclam &> /dev/null; then
  echo -e "${YELLOW}[•] Updating ClamAV virus database...${RESET}"
  freshclam
fi

# Make all Z-SHIELD scripts executable
echo -e "${YELLOW}[•] Setting executable permissions on all scripts...${RESET}"
chmod +x *.sh

echo -e "${GREEN}\n[✓] Z-SHIELD is ready to use.${RESET}"
echo -e "${CYAN}Run './zshield.sh' to start the toolkit.${RESET}\n"

