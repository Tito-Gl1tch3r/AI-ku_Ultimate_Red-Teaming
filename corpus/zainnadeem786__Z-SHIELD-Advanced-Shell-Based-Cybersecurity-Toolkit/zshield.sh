#!/bin/bash

# ================== Z-SHIELD v1.0 ====================
# Developed by ZAIN NADEEM | Offensive Security Toolkit
# =====================================================

# ──────[ Color Codes ]──────
RED="\033[1;31m"
GREEN="\033[1;32m"
CYAN="\033[1;36m"
YELLOW="\033[1;33m"
MAGENTA="\033[1;35m"
BLUE="\033[1;34m"
WHITE="\033[1;37m"
RESET="\033[0m"
BOLD="\033[1m"


# ──────[ Banner Function ]──────
banner() {
    clear
    echo -e "${GREEN}${BOLD}"
    echo "════════════════════════════════════════════════════"
    figlet -f ANSI_Shadow Z-SHIELD | lolcat
    echo -e "${CYAN}${BOLD}         Offensive & Defensive Cybersecurity Toolkit"
    echo -e "${YELLOW}               Developed by ${WHITE}ZAIN NADEEM"
    echo -e "${GREEN}════════════════════════════════════════════════════${RESET}\n"
   }

# ──────[ Exit Function ]──────
exit_zshield() {
    echo -e "\n${MAGENTA}╭────────────────────────────────────╮"
    echo -e "│  Exiting Z-SHIELD. Stay secure. 🛡️  │"
    echo -e "╰────────────────────────────────────╯${RESET}\n"
    exit 0
}

# ──────[ Load Selected Module ]──────
load_module() {
    case $1 in
        1)
            echo -e "${CYAN}[INFO] Running Reconnaissance Module...${RESET}" | tee -a "$LOG_FILE"
            bash modules/recon/recon.sh | tee -a "$LOG_FILE"
            ;;
        2)
            echo -e "${CYAN}[INFO] Running Exploitation Module...${RESET}" | tee -a "$LOG_FILE"
            bash modules/exploit/exploit.sh | tee -a "$LOG_FILE"
	    ;;

        3)
            echo -e "${CYAN}[INFO] Running Malware Analysis Module...${RESET}" | tee -a "$LOG_FILE"
            bash modules/malware/malware.sh | tee -a "$LOG_FILE"
            ;;
        4)
            echo -e "${CYAN}[INFO] Running Network Monitoring Module...${RESET}" | tee -a "$LOG_FILE"
            bash modules/netmon/netmon.sh | tee -a "$LOG_FILE"
            ;;
        0)
            exit_zshield
            ;;
        *)
            echo -e "${RED}Invalid option. Please select a valid module.${RESET}"
            ;;
    esac
    echo -ne "${YELLOW}\nPress Enter to return to main menu...${RESET}"
    read
    main_menu
}

# ──────[ Main Menu ]──────
main_menu() {
    echo -e "${MAGENTA}${BOLD}╭───────────────[ Main Menu ]───────────────╮"
    echo -e "${BLUE} 1.${RESET} Reconnaissance"
    echo -e "${BLUE} 2.${RESET} Exploitation"
    echo -e "${BLUE} 3.${RESET} Malware Analysis"
    echo -e "${BLUE} 4.${RESET} Network Monitoring"
    echo -e "${RED} 0.${RESET} Exit"
    echo -e "${MAGENTA}╰────────────────────────────────────────────╯${RESET}"
    echo -ne "${YELLOW}Enter your choice: ${RESET}"
    read choice
    load_module "$choice"
}

# ──────[ Help Menu ]──────
show_help() {
    echo -e "${CYAN}Usage: ./zshield.sh [option]${RESET}"
    echo -e "${YELLOW}Options:${RESET}"
    echo -e "  ${GREEN}-h, --help${RESET}        Show this help message"
    echo -e "  ${GREEN}-v, --version${RESET}     Show version information"
    echo -e "  ${GREEN}No option${RESET}          Launch the toolkit interface"
    exit 0
}

# ──────[ Version Info ]──────
show_version() {
    echo -e "${WHITE}Z-SHIELD v1.0 by ZAIN NADEEM${RESET}"
    exit 0
}

# ──────[ Parse CLI Args ]──────
case "$1" in
    -h|--help) show_help ;;
    -v|--version) show_version ;;
esac

# ──────[ Start Toolkit ]──────
banner
main_menu

