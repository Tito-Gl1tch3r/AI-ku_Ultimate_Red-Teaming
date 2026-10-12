#!/bin/bash

# Z-SHIELD Network Monitoring Module
# Author: ZAIN NADEEM

# Colors
RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
CYAN="\033[1;36m"
MAGENTA="\033[1;35m"
RESET="\033[0m"
BOLD="\033[1m"

# Banner
clear
echo -e "${GREEN}${BOLD}"
figlet -f ANSI_Shadow "NETWORK Module" | lolcat
echo -e "${CYAN}${BOLD}         Z-SHIELD Exploitation Module${RESET}"
echo -e "${YELLOW}          Developed by ${RESET}${WHITE}ZAIN NADEEM${RESET}"
echo ""

# List interfaces with numbers
echo -e "${YELLOW}[?] Available Network Interfaces:${RESET}"
interfaces=()
index=1
while IFS= read -r line; do
    iface=$(echo "$line" | awk -F: '{print $2}' | tr -d ' ')
    interfaces+=("$iface")
    echo " $index) $iface"
    ((index++))
done < <(ip -o link show)

# Get user input
read -p "$(echo -e ${CYAN}Select interface number to monitor:${RESET} )" iface_index
IFACE="${interfaces[$((iface_index-1))]}"

if [ -z "$IFACE" ]; then
    echo -e "${RED}[!] Invalid selection. Exiting.${RESET}"
    exit 1
fi

# Menu
while true; do
    echo -e "${CYAN}\nSelect monitoring option:${RESET}"
    echo -e "${GREEN}1) Live Packet Capture"
    echo -e "2) DNS Traffic Monitoring"
    echo -e "3) Show Interface Stats"
    echo -e "4) Exit${RESET}"
    read -p "$(echo -e ${YELLOW}Choose option [1-4]: ${RESET})" OPTION

    case $OPTION in
        1)
            echo -e "${GREEN}\n[✓] Starting live packet capture on $IFACE... (Press Ctrl+C to stop)${RESET}"
            echo -e "${CYAN}+---------------------+-------------------------------+--------+-----------------------------+${RESET}"
            printf "${CYAN}| %-19s | %-29s | %-6s | %-27s |\n" "TIME" "SRC → DST" "PROTO" "INFO"
            echo -e "${CYAN}+---------------------+-------------------------------+--------+-----------------------------+${RESET}"
            sudo tcpdump -i "$IFACE" -nn -l -q -tt | \
            awk -F' ' '
            {
                time=strftime("%H:%M:%S", $1);
                src=$3;
                dst=$5;
                gsub(":", "", dst);
                proto=$6;
                info="";
                for(i=7; i<=NF; i++) info=info" "$i;
                printf "\033[1;36m| %-19s | %-29s | %-6s | %-27s |\033[0m\n", time, src " → " dst, proto, substr(info,1,27)
            }'
            ;;
        2)
            echo -e "${GREEN}\n[✓] Monitoring DNS queries on $IFACE (port 53)... (Press Ctrl+C to stop)${RESET}"
            echo -e "${CYAN}+---------------------+-------------------------------+---------------------------+${RESET}"
            printf "${CYAN}| %-19s | %-29s | %-25s |\n" "TIME" "CLIENT IP" "QUERY / RESPONSE"
            echo -e "${CYAN}+---------------------+-------------------------------+---------------------------+${RESET}"
            sudo tcpdump -i "$IFACE" port 53 -l -nn -tt | \
            awk '
            /A\?/ {
                time=strftime("%H:%M:%S", $1);
                client=$3;
                gsub("\\.", "", client);
                domain=$NF;
                printf "\033[1;36m| %-19s | %-29s | %-25s |\033[0m\n", time, client, domain
            }'
            ;;
        3)
            echo -e "${GREEN}\n[✓] Interface statistics for ${IFACE}:${RESET}"
            echo -e "${CYAN}"
            ip -s link show "$IFACE"
            echo -e "${RESET}"
            ;;
        4)
            echo -e "${MAGENTA}[✓] Exiting Z-SHIELD Network Module. Stay secure.${RESET}"
            break
            ;;
        *)
            echo -e "${RED}[!] Invalid choice. Please select between 1–4.${RESET}"
            ;;
    esac
done

