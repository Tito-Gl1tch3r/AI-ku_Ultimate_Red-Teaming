#!/bin/bash

# Define color codes for terminal output
HEADER='\033[38;5;81m'
SUCCESS='\033[38;5;83m'
ERROR='\033[38;5;196m'
INFO='\033[38;5;144m'
RESET='\033[0m'
PROGRESS='\033[38;5;39m'
BOLD='\033[1m'

# Tool metadata
TOOL_NAME="X3bounty"
DEVELOPER="X3NIDE"
GITHUB="https://github.com/mubbashirulislam"
VERSION="1.2"

# Directory to store results
RESULTS_DIR="$HOME/.x3bounty_results"

# Function to display the banner
show_banner() {
    clear
    echo -e "${HEADER}"
    cat << "EOF"
██╗  ██╗██████╗ ██████╗  ██████╗ ██╗   ██╗███╗   ██╗████████╗██╗   ██╗
╚██╗██╔╝╚════██╗██╔══██╗██╔═══██╗██║   ██║████╗  ██║╚══██╔══╝╚██╗ ██╔╝
 ╚███╔╝  █████╔╝██████╔╝██║   ██║██║   ██║██╔██╗ ██║   ██║    ╚████╔╝ 
 ██╔██╗  ╚═══██╗██╔══██╗██║   ██║██║   ██║██║╚██╗██║   ██║     ╚██╔╝  
██╔╝ ██╗██████╔╝██████╔╝╚██████╔╝╚██████╔╝██║ ╚████║   ██║      ██║   
╚═╝  ╚═╝╚═════╝ ╚═════╝  ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝   ╚═╝      ╚═╝   
EOF
    echo -e "${RESET}${BOLD}       [ Developed by: ${HEADER}$DEVELOPER | Version: ${HEADER}$VERSION ]${RESET}"
    echo -e "       [ GitHub: ${HEADER}$GITHUB ${RESET}]"
    echo -e "${RESET}${HEADER}═══════════════════════════════════════════════════════════════════${RESET}\n"
}

# Redesigned function to display a progress bar with animation
progress_bar() {
    local duration=$1
    local width=50
    local progress=0
    local fill_char="▓"
    local empty_char="░"
    local spinner=('/' '-' '\' '|')

    while [ $progress -le 100 ]; do
        local fill=$(($progress * $width / 100))
        local empty=$(($width - $fill))
        local spin_index=$((progress % 4))
        
        printf "\r${PROGRESS}[${RESET}"
        printf "%${fill}s" "" | tr " " "${fill_char}"
        printf "%${empty}s" "" | tr " " "${empty_char}"
        printf "${PROGRESS}] ${RESET}${progress}%% ${spinner[$spin_index]}"
        
        progress=$(($progress + 2))
        sleep $duration
    done
    echo
}

# Function to check if required tools are installed
check_requirements() {
    local tools=("dig" "host" "curl" "jq" "nmap" "whois")
    local missing_tools=()
    
    echo -e "${INFO}[*] Checking if we have everything we need...${RESET}"
    
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        echo -e "${ERROR}[!] Oops! We're missing: ${missing_tools[*]}${RESET}"
        echo -e "${INFO}[*] You can install them with: sudo apt install ${missing_tools[*]}${RESET}"
        exit 1
    fi
    echo -e "${SUCCESS}[+] WELL WELL WELL! We have all the tools we need. Lesgoo${RESET}"
}

# Function to perform a WHOIS lookup
whois_lookup() {
    local target=$1
    local whois_file="whois_${target}.txt"
    
    echo -e "${INFO}[*] Getting WHOIS info for: ${target}${RESET}"
    
    if ! whois "$target" > "$whois_file" 2>/dev/null; then
        echo -e "${ERROR}[!] WHOIS lookup failed for ${target}${RESET}"
        return 1
    fi
    
    echo -e "\n${INFO}[*] WHOIS Information:${RESET}"
    echo -e "${HEADER}═══════════════════════════════════════════════════════════════════${RESET}"
    grep -E "Domain Name:|Registrar:|Creation Date:|Registry Expiry Date:|Registrant Organization:" "$whois_file"
    echo -e "${HEADER}═══════════════════════════════════════════════════════════════════${RESET}"
    echo -e "${SUCCESS}[+] Full WHOIS data saved to: $whois_file${RESET}"
}

# Enhanced function to validate a subdomain
validate_subdomain() {
    local subdomain=$1
    local is_valid=false
    local timeout=5

    # Check DNS resolution
    if host "$subdomain" >/dev/null 2>&1; then
        # Get IP addresses
        local ips=($(dig +short "$subdomain" A; dig +short "$subdomain" AAAA))
        
        if [ ${#ips[@]} -gt 0 ]; then
            for ip in "${ips[@]}"; do
                # Skip private IP ranges
                if [[ ! $ip =~ ^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.) ]]; then
                    # Try HTTP connection with timeout
                    if curl -s --max-time $timeout -I "http://${subdomain}" >/dev/null 2>&1 || \
                       curl -s --max-time $timeout -I "https://${subdomain}" >/dev/null 2>&1; then
                        is_valid=true
                        break
                    fi
                fi
            done
        fi
    fi

    $is_valid
}

# Function to normalize a subdomain
normalize_subdomain() {
    local subdomain=$1
    echo "$subdomain" | \
        tr '[:upper:]' '[:lower:]' | \
        sed -E 's/^[*\.]+//;s/[[:space:]]*$//;s/^\.+//;s/\.+$//' | \
        grep -E '^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*\.[a-z]{2,}$'
}

# Enhanced function to find active subdomains
find_active_subdomains() {
    local target=$1
    local temp_file="temp_subdomains.txt"
    local output_file="active_subdomains.txt"
    local verified_file="verified_subdomains.txt"
    local max_concurrent=10
    local total_processed=0
    
    echo -e "${INFO}[*] Looking for subdomains of: $target${RESET}"
    
    # Create temporary files
    touch "$temp_file"
    
    # Collect subdomains from multiple sources
    {
        echo -e "${INFO}[*] Checking crt.sh...${RESET}"
        curl -s "https://crt.sh/?q=%25.$target&output=json" | \
            jq -r '.[].name_value' 2>/dev/null | \
            grep -i ".*\.$target$" >> "$temp_file"
            
        # SecurityTrails (if API key is available)
        if [ ! -z "$SECURITYTRAILS_API_KEY" ]; then
            echo -e "${INFO}[*] Checking SecurityTrails...${RESET}"
            curl -s --header "apikey: $SECURITYTRAILS_API_KEY" \
                "https://api.securitytrails.com/v1/domain/$target/subdomains" | \
                jq -r '.subdomains[]' 2>/dev/null | \
                awk -v domain=".$target" '{print $0 domain}' >> "$temp_file"
        fi
        
        # Use amass if available
        if command -v amass &> /dev/null; then
            echo -e "${INFO}[*] Running amass scan...${RESET}"
            amass enum -passive -d "$target" 2>/dev/null >> "$temp_file"
        fi
    } &
    wait
    
    if [ -f "$temp_file" ]; then
        # Normalize and deduplicate
        sort -u "$temp_file" | while IFS= read -r subdomain; do
            normalized_subdomain=$(normalize_subdomain "$subdomain")
            if [ ! -z "$normalized_subdomain" ]; then
                echo "$normalized_subdomain"
            fi
        done > "$output_file"
        
        total_subdomains=$(wc -l < "$output_file")
        echo -e "${INFO}[*] Found $total_subdomains potential subdomains. Validating...${RESET}"
        
        # Process subdomains with progress bar
        while IFS= read -r subdomain; do
            ((total_processed++))
            progress_bar 0.1
            
            (
                if validate_subdomain "$subdomain"; then
                    echo "$subdomain" >> "$verified_file.tmp"
                fi
            ) &
            
            # Control parallel processes
            if (( total_processed % max_concurrent == 0 )); then
                wait
            fi
        done < "$output_file"
        wait
        
        echo -e "\n"
        
        # Finalize results
        if [ -f "$verified_file.tmp" ]; then
            sort -u "$verified_file.tmp" > "$verified_file"
            rm "$verified_file.tmp"
            
            # Move verified results to output file
            mv "$verified_file" "$output_file"
            
            total_active=$(wc -l < "$output_file")
            echo -e "${SUCCESS}[+] Found $total_active live subdomains out of $total_subdomains discovered${RESET}"
            
            echo -e "\n${INFO}[*] Active Subdomains:${RESET}"
            echo -e "${HEADER}═══════════════════════════════════════════════════════════════════${RESET}"
            cat "$output_file"
            echo -e "${HEADER}═══════════════════════════════════════════════════════════════════${RESET}"
        else
            echo -e "${ERROR}[!] No live subdomains found${RESET}"
            touch "$output_file"
        fi
    else
        echo -e "${ERROR}[!] Couldn't find any subdomains${RESET}"
    fi
    
    # Cleanup
    rm -f "$temp_file" 2>/dev/null
}

# Function to set up the workspace
setup_workspace() {
    local target=$1
    workspace="$RESULTS_DIR/x3bounty_${target}_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$workspace"
    cd "$workspace" || exit 1
    echo -e "${SUCCESS}[+] Created new workspace: $workspace${RESET}"
}

# Function to start a scan
start_scan() {
    local target=$1
    if [[ ! $target =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}$ ]]; then
        echo -e "${ERROR}[!] Invalid domain format: $target${RESET}"
        return 1
    fi
    
    setup_workspace "$target"
    
    # Run scans in parallel
    whois_lookup "$target" &
    find_active_subdomains "$target" &
    wait
    
    # Save scan info
    {
        echo "Scan completed on: $(date)"
        echo "Target: $target"
        echo "Total active subdomains: $(wc -l < active_subdomains.txt 2>/dev/null || echo 0)"
    } > scan_info.txt
    
    echo -e "${SUCCESS}[+] All done! Results saved in: $workspace${RESET}"
}

# Function to view previous results
view_previous_results() {
    echo -e "\n${INFO}[*] Looking for previous scans...${RESET}"
    
    if [ ! -d "$RESULTS_DIR" ]; then
        echo -e "${ERROR}[!] No previous scans found${RESET}"
        return
    fi
    
    cd "$RESULTS_DIR" 2>/dev/null || {
        echo -e "${ERROR}[!] Could not access results directory${RESET}"
        return
    }
    
    local scan_folders=(x3bounty_*)
    
    if [ "${scan_folders[0]}" = "x3bounty_*" ]; then
        echo -e "${ERROR}[!] No previous scans found${RESET}"
        return
    fi
    
    echo -e "${SUCCESS}[+] Found these previous scans:${RESET}"
    echo -e "${HEADER}═══════════════════════════════════════════════════════════════════${RESET}"
    
    select folder in "${scan_folders[@]}" "Back to main menu"; do
        if [ "$folder" = "Back to main menu" ]; then
            break
        elif [ -n "$folder" ]; then
            echo -e "\n${INFO}[*] Showing results for: $folder${RESET}"
            echo -e "${HEADER}═══════════════════════════════════════════════════════════════════${RESET}"
            
            if [ -f "$folder/scan_info.txt" ]; then
                cat "$folder/scan_info.txt"
                echo
            fi
            
            if [ -f "$folder/active_subdomains.txt" ]; then
                echo -e "${INFO}[*] Found Subdomains:${RESET}"
                cat "$folder/active_subdomains.txt"
            fi
            
            echo -e "${HEADER}═══════════════════════════════════════════════════════════════════${RESET}"
            read -p "Press Enter to continue..."
            break
        fi
    done
}

# Function to handle exit
cleanup() {
    echo -e "\n${INFO}[*] Cleaning up...${RESET}"
    # Remove any temporary files
    find /tmp -name "x3bounty_*" -type f -delete 2>/dev/null
    echo -e "${SUCCESS}[+] Thanks for using X3bounty!${RESET}"
    exit 0
}

# Set up trap for clean exit
trap cleanup SIGINT SIGTERM

# Function to show help
show_help() {
    echo -e "\n${BOLD}Usage:${RESET}"
    echo -e "  $0 [options]"
    echo -e "\n${BOLD}Options:${RESET}"
    echo -e "  -h, --help     Show this help message"
    echo -e "  -t, --target   Specify target domain"
    echo -e "  -v, --version  Show version information"
    echo -e "  -l, --list     List previous scan results"
    echo -e "\n${BOLD}Examples:${RESET}"
    echo -e "  $0 -t example.com"
    echo -e "  $0 --list"
}

# Function to show the menu
show_menu() {
    echo -e "\n${BOLD}What would you like to do?${RESET}"
    echo -e "${HEADER}[1] Start a new scan${RESET}"
    echo -e "${HEADER}[2] View previous results${RESET}"
    echo -e "${HEADER}[3] Show help${RESET}"
    echo -e "${HEADER}[4] Exit${RESET}"
    
    read -p "Enter your choice (1-4): " choice
    
    case $choice in
        1)
            read -p "Enter target domain (e.g., example.com): " target
            if [ -n "$target" ]; then
                start_scan "$target"
            else
                echo -e "${ERROR}[!] No target specified${RESET}"
            fi
            ;;
        2)
            view_previous_results
            ;;
        3)
            show_help
            ;;
        4)
            cleanup
            ;;
        *)
            echo -e "${ERROR}[!] Invalid choice${RESET}"
            ;;
    esac
}

# Main execution
main() {
    # Create results directory if it doesn't exist
    mkdir -p "$RESULTS_DIR"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--version)
                echo -e "${INFO}${TOOL_NAME} version ${VERSION}${RESET}"
                exit 0
                ;;
            -t|--target)
                target="$2"
                shift
                shift
                ;;
            -l|--list)
                view_previous_results
                exit 0
                ;;
            *)
                echo -e "${ERROR}[!] Unknown option: $1${RESET}"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Show banner
    show_banner
    
    # Check requirements
    check_requirements
    
    # If target is specified via command line, run scan directly
    if [ -n "$target" ]; then
        start_scan "$target"
        exit 0
    fi
    
    # Otherwise, show interactive menu
    while true; do
        show_menu
    done
}

# Check if script is being run as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${ERROR}[!] This script shouldn't be run as root${RESET}"
    exit 1
fi

# Start the script
main "$@"