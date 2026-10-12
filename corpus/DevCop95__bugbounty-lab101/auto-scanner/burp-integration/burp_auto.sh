#!/bin/bash
# ============================================
# Burp Suite GUI Automation
# ============================================
# Controls Burp Suite through screenshots,
# clicks and mouse/keyboard movements.
#
# Usage: ./burp_auto.sh <command> [options]
# ============================================

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCREENSHOTS_DIR="$SCRIPT_DIR/screenshots"
mkdir -p "$SCREENSHOTS_DIR"

# ============================================
# HELPER FUNCTIONS
# ============================================

# Take screenshot
take_screenshot() {
    local name="${1:-screenshot_$(date +%Y%m%d_%H%M%S)}"
    scrot "$SCREENSHOTS_DIR/${name}.png" 2>/dev/null
    echo -e "${GREEN}[✓] Screenshot: $SCREENSHOTS_DIR/${name}.png${NC}"
}

# Find window by name
find_window() {
    local title="$1"
    xdotool search --name "$title" 2>/dev/null | head -1
}

# Activate window
activate_window() {
    local wid="$1"
    if [ -n "$wid" ]; then
        xdotool windowactivate "$wid" 2>/dev/null
        xdotool windowfocus "$wid" 2>/dev/null
        sleep 0.5
        return 0
    fi
    return 1
}

# Click at coordinates
click_at() {
    local x="$1"
    local y="$2"
    local delay="${3:-0.3}"
    xdotool mousemove "$x" "$y"
    sleep 0.2
    xdotool click 1
    sleep "$delay"
}

# Double click
double_click_at() {
    local x="$1"
    local y="$2"
    xdotool mousemove "$x" "$y"
    sleep 0.2
    xdotool click --repeat 2 1
    sleep 0.5
}

# Type text
type_text() {
    local text="$1"
    local delay="${2:-0.05}"
    xdotool type --delay "$(echo "$delay * 1000" | bc)" "$text"
    sleep 0.3
}

# Paste from clipboard
paste_text() {
    local text="$1"
    echo -n "$text" | xclip -selection clipboard
    xdotool key ctrl+v
    sleep 0.3
}

# Press key
press_key() {
    local key="$1"
    xdotool key "$key"
    sleep 0.2
}

# Find text on screen using OCR (if available)
find_text_on_screen() {
    local text="$1"
    local screenshot="$SCREENSHOTS_DIR/current.png"
    
    # Take screenshot
    scrot "$screenshot" 2>/dev/null
    
    # Find text using tesseract (if available)
    if command -v tesseract &>/dev/null; then
        tesseract "$screenshot" stdout 2>/dev/null | grep -n "$text" | head -5
    else
        echo -e "${YELLOW}[!] tesseract not installed for OCR${NC}"
        return 1
    fi
}

# ============================================
# BURP SUITE COMMANDS
# ============================================

# Launch Burp Suite
launch_burp() {
    echo -e "${YELLOW}[→] Launching Burp Suite...${NC}"
    
    # Find Burp Suite
    BURP_PATHS=(
        "/usr/bin/burpsuite"
        "/opt/BurpSuiteCommunity/burpsuite"
        "/opt/BurpSuiteProfessional/burpsuite"
        "$HOME/BurpSuiteCommunity/burpsuite"
        "$HOME/BurpSuiteProfessional/burpsuite"
    )
    
    for path in "${BURP_PATHS[@]}"; do
        if [ -f "$path" ] || [ -f "$path.sh" ]; then
            "$path" &
            sleep 5
            take_screenshot "burp_launched"
            echo -e "${GREEN}[✓] Burp Suite launched${NC}"
            return 0
        fi
    done
    
    # Try with command
    if command -v burpsuite &>/dev/null; then
        burpsuite &
        sleep 5
        take_screenshot "burp_launched"
        echo -e "${GREEN}[✓] Burp Suite launched${NC}"
        return 0
    fi
    
    echo -e "${RED}[✗] Burp Suite not found${NC}"
    return 1
}

# Wait for Burp to be ready
wait_for_burp() {
    echo -e "${YELLOW}[→] Waiting for Burp Suite to be ready...${NC}"
    
    local max_wait=30
    local count=0
    
    while [ $count -lt $max_wait ]; do
        local wid
    wid=$(find_window "Burp Suite")
        if [ -n "$wid" ]; then
            echo -e "${GREEN}[✓] Burp Suite is ready${NC}"
            take_screenshot "burp_ready"
            return 0
        fi
        sleep 1
        ((count++))
    done
    
    echo -e "${RED}[✗] Timeout waiting for Burp Suite${NC}"
    return 1
}

# Enable Proxy in Burp
enable_proxy() {
    echo -e "${YELLOW}[→] Enabling Proxy in Burp...${NC}"
    
    local wid
    wid=$(find_window "Burp Suite")
    if [ -z "$wid" ]; then
        echo -e "${RED}[✗] Burp Suite not found${NC}"
        return 1
    fi
    
    activate_window "$wid"
    
    # Click on "Proxy" tab
    click_at 150 120
    sleep 0.5
    
    # Click on "Options"
    click_at 250 150
    sleep 0.5
    
    # Click on "Intercept" tab
    click_at 350 150
    sleep 0.5
    
    # Click on "Intercept is on/off"
    click_at 200 300
    sleep 0.5
    
    take_screenshot "proxy_enabled"
    echo -e "${GREEN}[✓] Proxy enabled${NC}"
}

# Open Target in Burp
open_target() {
    local url="$1"
    echo -e "${YELLOW}[→] Opening $url in Burp...${NC}"
    
    local wid
    wid=$(find_window "Burp Suite")
    if [ -z "$wid" ]; then
        echo -e "${RED}[✗] Burp Suite not found${NC}"
        return 1
    fi
    
    activate_window "$wid"
    
    # Click on "Target" tab
    click_at 50 120
    sleep 0.5
    
    # Click on "Scope"
    click_at 100 200
    sleep 0.5
    
    # Click on "Add"
    click_at 400 250
    sleep 0.5
    
    # Type URL
    type_text "$url"
    sleep 0.3
    
    # Click on OK
    click_at 400 350
    sleep 0.5
    
    take_screenshot "target_added"
    echo -e "${GREEN}[✓] Target added: $url${NC}"
}

# Start Spider
start_spider() {
    local url="$1"
    echo -e "${YELLOW}[→] Starting Spider for $url...${NC}"
    
    local wid
    wid=$(find_window "Burp Suite")
    if [ -z "$wid" ]; then
        echo -e "${RED}[✗] Burp Suite not found${NC}"
        return 1
    fi
    
    activate_window "$wid"
    
    # Click on "Target" tab
    click_at 50 120
    sleep 0.5
    
    # Right click on the URL
    click_at 200 250  # Left click first
    sleep 0.3
    
    # Find "Spider this host"
    # (This varies depending on the Burp version)
    
    take_screenshot "spider_started"
    echo -e "${GREEN}[✓] Spider started${NC}"
}

# Start Active Scan
start_scan() {
    local url="$1"
    echo -e "${YELLOW}[→] Starting Active Scan for $url...${NC}"
    
    local wid
    wid=$(find_window "Burp Suite")
    if [ -z "$wid" ]; then
        echo -e "${RED}[✗] Burp Suite not found${NC}"
        return 1
    fi
    
    activate_window "$wid"
    
    # Click on "Target" tab
    click_at 50 120
    sleep 0.5
    
    # Right click on the URL
    click_at 200 250
    sleep 0.3
    
    # Find "Scan"
    # (This varies depending on the Burp version)
    
    take_screenshot "scan_started"
    echo -e "${GREEN}[✓] Active Scan started${NC}"
}

# View Issues
view_issues() {
    echo -e "${YELLOW}[→] Opening Issues...${NC}"
    
    local wid
    wid=$(find_window "Burp Suite")
    if [ -z "$wid" ]; then
        echo -e "${RED}[✗] Burp Suite not found${NC}"
        return 1
    fi
    
    activate_window "$wid"
    
    # Click on "Target" tab
    click_at 50 120
    sleep 0.5
    
    # Click on "Issues"
    click_at 100 400
    sleep 0.5
    
    take_screenshot "issues_view"
    echo -e "${GREEN}[✓] Issues displayed${NC}"
}

# Export Issues
export_issues() {
    echo -e "${YELLOW}[→] Exporting Issues...${NC}"
    
    local wid
    wid=$(find_window "Burp Suite")
    if [ -z "$wid" ]; then
        echo -e "${RED}[✗] Burp Suite not found${NC}"
        return 1
    fi
    
    activate_window "$wid"
    
    # Click on "Project"
    click_at 50 50
    sleep 0.5
    
    # Click on "Save project"
    click_at 100 100
    sleep 0.5
    
    # Type name
    type_text "burp_project_$(date +%Y%m%d)"
    sleep 0.3
    
    # Click on Save
    click_at 400 400
    sleep 1
    
    take_screenshot "project_saved"
    echo -e "${GREEN}[✓] Project saved${NC}"
}

# Take screenshot and analyze
analyze_screen() {
    echo -e "${YELLOW}[→] Analyzing screen...${NC}"
    
    take_screenshot "analysis_$(date +%Y%m%d_%H%M%S)"
    
    # Check if tesseract is available
    if command -v tesseract &>/dev/null; then
        local screenshot
        screenshot="$SCREENSHOTS_DIR/analysis_$(date +%Y%m%d_%H%M%S).png"
        tesseract "$screenshot" stdout 2>/dev/null | head -50
    else
        echo -e "${YELLOW}[!] For OCR install: sudo apt install tesseract-ocr${NC}"
    fi
}

# Show Burp status
show_burp_status() {
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  Burp Suite Status${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Check if Burp is running
    local burp_pid
    burp_pid=$(pgrep -f "burpsuite" 2>/dev/null)
    if [ -n "$burp_pid" ]; then
        echo -e "${GREEN}[✓] Burp Suite is running (PID: $burp_pid)${NC}"
    else
        echo -e "${RED}[✗] Burp Suite is NOT running${NC}"
    fi
    
    # Check window
    local wid
    wid=$(find_window "Burp Suite")
    if [ -n "$wid" ]; then
        echo -e "${GREEN}[✓] Burp Suite window found (WID: $wid)${NC}"
    else
        echo -e "${RED}[✗] Burp Suite window not found${NC}"
    fi
    
    echo ""
    echo -e "${CYAN}Available tools:${NC}"
    echo "  xdotool: $(which xdotool 2>/dev/null || echo 'no')"
    echo "  scrot: $(which scrot 2>/dev/null || echo 'no')"
    echo "  xclip: $(which xclip 2>/dev/null || echo 'no')"
    echo "  tesseract: $(which tesseract 2>/dev/null || echo 'no')"
}

# ============================================
# MAIN
# ============================================

case "${1:-help}" in
    launch)
        launch_burp
        ;;
    wait)
        wait_for_burp
        ;;
    proxy)
        enable_proxy
        ;;
    target)
        open_target "$2"
        ;;
    spider)
        start_spider "$2"
        ;;
    scan)
        start_scan "$2"
        ;;
    issues)
        view_issues
        ;;
    export)
        export_issues
        ;;
    screenshot)
        take_screenshot "${2:-manual}"
        ;;
    analyze)
        analyze_screen
        ;;
    status)
        show_burp_status
        ;;
    click)
        click_at "$2" "$3"
        ;;
    type)
        type_text "$2"
        ;;
    paste)
        paste_text "$2"
        ;;
    key)
        press_key "$2"
        ;;
    *)
        echo ""
        echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║         Burp Suite GUI Automation - Help                    ║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo "Usage: $0 <command> [options]"
        echo ""
        echo "Commands:"
        echo "  launch              - Launch Burp Suite"
        echo "  wait                - Wait for Burp to be ready"
        echo "  status              - View Burp status"
        echo "  proxy               - Enable Proxy"
        echo "  target <url>        - Add target"
        echo "  spider <url>        - Start Spider"
        echo "  scan <url>          - Start Active Scan"
        echo "  issues              - View Issues"
        echo "  export              - Export project"
        echo "  screenshot [name]   - Take screenshot"
        echo "  analyze             - Analyze screen"
        echo "  click <x> <y>       - Click at coordinates"
        echo "  type <text>         - Type text"
        echo "  paste <text>        - Paste text"
        echo "  key <key>           - Press key"
        echo ""
        echo "Examples:"
        echo "  $0 launch"
        echo "  $0 target https://ejemplo.com"
        echo "  $0 scan https://ejemplo.com"
        echo "  $0 screenshot burp_test"
        echo ""
        ;;
esac
