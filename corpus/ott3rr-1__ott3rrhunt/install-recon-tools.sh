#!/usr/bin/env bash
set -euo pipefail

# Install additional recon tools for bug bounty hunting
# Kali Linux / Debian-based systems
# Supports both bash and zsh

# Colors
bold=$(tput bold 2>/dev/null || echo "")
green=$(tput setaf 2 2>/dev/null || echo "")
yellow=$(tput setaf 3 2>/dev/null || echo "")
cyan=$(tput setaf 6 2>/dev/null || echo "")
red=$(tput setaf 1 2>/dev/null || echo "")
reset=$(tput sgr0 2>/dev/null || echo "")

echo "${bold}${cyan}================================================${reset}"
echo "${bold}${cyan}  Bug Bounty Recon Tools Installer${reset}"
echo "${bold}${cyan}================================================${reset}"
echo

# Detect shell and set appropriate RC file
detect_shell() {
  # First check SHELL environment variable (most reliable)
  case "$SHELL" in
    */zsh) echo "zsh" ;;
    */bash) echo "bash" ;;
    *)
      # Fallback: check version variables
      if [[ -n "${ZSH_VERSION:-}" ]]; then
        echo "zsh"
      elif [[ -n "${BASH_VERSION:-}" ]]; then
        echo "bash"
      else
        echo "bash" # default to bash
      fi
      ;;
  esac
}

DETECTED_SHELL=$(detect_shell)
if [[ "$DETECTED_SHELL" == "zsh" ]]; then
  RC_FILE="$HOME/.zshrc"
  echo "${bold}${cyan}Detected shell: zsh${reset}"
else
  RC_FILE="$HOME/.bashrc"
  echo "${bold}${cyan}Detected shell: bash${reset}"
fi
echo "  Using config file: ${bold}${RC_FILE}${reset}"
echo

# Setup directories
TOOLS_DIR="${HOME}/tools"
BIN_DIR="${HOME}/.local/bin"

echo "${bold}Setting up directories...${reset}"
mkdir -p "$TOOLS_DIR"
mkdir -p "$BIN_DIR"
echo "  ✓ Tools directory: $TOOLS_DIR"
echo "  ✓ Binaries directory: $BIN_DIR"
echo

# Check if Go is installed
if ! command -v go >/dev/null 2>&1; then
  echo "${bold}${red}Go is not installed!${reset}"
  echo "Installing Go..."
  
  # Install Go via apt (Kali usually has it)
  if command -v apt >/dev/null 2>&1; then
    sudo apt update
    sudo apt install -y golang
  else
    echo "${red}Please install Go manually: https://golang.org/dl/${reset}"
    exit 1
  fi
  
  # Setup Go environment in detected shell RC file
  if ! grep -q "export GOPATH=" "$RC_FILE" 2>/dev/null; then
    echo "" >> "$RC_FILE"
    echo "# Go environment" >> "$RC_FILE"
    echo "export GOPATH=\$HOME/go" >> "$RC_FILE"
    echo "export PATH=\$PATH:\$GOPATH/bin" >> "$RC_FILE"
  fi
  
  export GOPATH=$HOME/go
  export PATH=$PATH:$GOPATH/bin
  
  echo "${green}✓ Go installed${reset}"
else
  echo "${green}✓ Go is already installed: $(go version)${reset}"
fi
echo

# Ensure GOPATH and PATH are set
export GOPATH=${GOPATH:-$HOME/go}
export PATH=$PATH:$GOPATH/bin:$BIN_DIR

# Function to check if a tool is installed
check_tool() {
  if command -v "$1" >/dev/null 2>&1; then
    echo "${green}✓ $1 is already installed${reset}"
    return 0
  else
    echo "${yellow}✗ $1 not found, installing...${reset}"
    return 1
  fi
}

# Install assetfinder
echo "${bold}${cyan}[1/5] Installing assetfinder...${reset}"
if check_tool assetfinder; then
  assetfinder -h 2>&1 | head -n1 || echo "  (installed)"
else
  go install github.com/tomnomnom/assetfinder@latest
  echo "${green}✓ assetfinder installed${reset}"
fi
echo

# Install amass
echo "${bold}${cyan}[2/5] Installing amass...${reset}"
if check_tool amass; then
  amass -version 2>/dev/null || amass -h 2>&1 | head -n1 || echo "  (installed)"
else
  # Try apt first (Kali has it in repos)
  if sudo apt install -y amass 2>/dev/null; then
    echo "${green}✓ amass installed via apt${reset}"
  else
    # Fallback to go install
    go install -v github.com/owasp-amass/amass/v4/...@master
    echo "${green}✓ amass installed via Go${reset}"
  fi
fi
echo

# Install gau (GetAllUrls)
echo "${bold}${cyan}[3/5] Installing gau...${reset}"
if check_tool gau; then
  gau -h 2>&1 | head -n1 || echo "  (installed)"
else
  go install github.com/lc/gau/v2/cmd/gau@latest
  echo "${green}✓ gau installed${reset}"
fi
echo

# Install anew (append new lines to file)
echo "${bold}${cyan}[4/5] Installing anew...${reset}"
if check_tool anew; then
  echo "${green}✓ anew available${reset}"
else
  go install github.com/tomnomnom/anew@latest
  echo "${green}✓ anew installed${reset}"
fi
echo

# Install unfurl (URL parsing)
echo "${bold}${cyan}[5/5] Installing unfurl...${reset}"
if check_tool unfurl; then
  unfurl -h 2>&1 | head -n1 || echo "  (installed)"
else
  go install github.com/tomnomnom/unfurl@latest
  echo "${green}✓ unfurl installed${reset}"
fi
echo

# Setup gf (pattern matching) and patterns
echo "${bold}${cyan}Setting up gf patterns...${reset}"
if ! command -v gf >/dev/null 2>&1; then
  echo "Installing gf..."
  go install github.com/tomnomnom/gf@latest
fi

# Install gf patterns if not present
GF_DIR="${HOME}/.gf"
if [[ ! -d "$GF_DIR" ]] || [[ -z "$(ls -A $GF_DIR 2>/dev/null)" ]]; then
  echo "Installing gf patterns..."
  mkdir -p "$GF_DIR"
  if git clone https://github.com/1ndianl33t/Gf-Patterns.git /tmp/gf-patterns 2>/dev/null; then
    cp /tmp/gf-patterns/*.json "$GF_DIR/" 2>/dev/null || true
    rm -rf /tmp/gf-patterns
    echo "${green}✓ gf patterns installed${reset}"
  else
    echo "${yellow}⚠ Could not clone gf patterns (not critical)${reset}"
  fi
else
  echo "${green}✓ gf patterns already exist${reset}"
fi
echo

# Add to PATH in RC file if not already there
echo "${bold}${cyan}Configuring PATH in ${RC_FILE}...${reset}"

add_to_path() {
  local path_to_add=$1
  if ! grep -q "export PATH=.*${path_to_add}" "$RC_FILE" 2>/dev/null; then
    echo "export PATH=\$PATH:${path_to_add}" >> "$RC_FILE"
    echo "  ✓ Added ${path_to_add} to PATH in ${RC_FILE}"
  else
    echo "  ✓ ${path_to_add} already in PATH"
  fi
}

# Ensure GOPATH is set
if ! grep -q "export GOPATH=" "$RC_FILE" 2>/dev/null; then
  echo "" >> "$RC_FILE"
  echo "# Go environment" >> "$RC_FILE"
  echo "export GOPATH=\$HOME/go" >> "$RC_FILE"
  echo "  ✓ Added GOPATH to ${RC_FILE}"
fi

add_to_path "\$HOME/go/bin"
add_to_path "\$HOME/.local/bin"

echo

# Update current session PATH
export PATH=$PATH:$HOME/go/bin:$HOME/.local/bin

# Verify installations
echo "${bold}${cyan}================================================${reset}"
echo "${bold}${cyan}  Verification${reset}"
echo "${bold}${cyan}================================================${reset}"
echo

verify_tool() {
  if command -v "$1" >/dev/null 2>&1; then
    version=$($1 ${2:--h} 2>&1 | head -n1 | cut -c1-60)
    echo "${green}✓${reset} ${bold}$1${reset}: $version"
    return 0
  else
    echo "${red}✗${reset} ${bold}$1${reset}: not found in PATH"
    return 1
  fi
}

# Track if all tools verified
all_verified=true

verify_tool assetfinder || all_verified=false
verify_tool amass -version || all_verified=false
verify_tool gau || all_verified=false
verify_tool anew || all_verified=false
verify_tool unfurl || all_verified=false
verify_tool gf || all_verified=false
echo "${bold}${cyan}Core recon tools (should already be installed):${reset}"
verify_tool subfinder -version || echo "${yellow}  (install with: go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest)${reset}"
verify_tool httpx -version || echo "${yellow}  (install with: go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest)${reset}"
verify_tool waybackurls || echo "${yellow}  (install with: go install github.com/tomnomnom/waybackurls@latest)${reset}"

echo
echo "${bold}${cyan}================================================${reset}"
echo "${bold}${green}Installation complete!${reset}"
echo "${bold}${cyan}================================================${reset}"
echo

if [[ "$all_verified" == "false" ]]; then
  echo "${bold}${yellow}⚠️  Some tools not found in current PATH${reset}"
  echo
  echo "${bold}This is normal! Run this command:${reset}"
  echo "${bold}${cyan}source ${RC_FILE}${reset}"
  echo
  echo "Or close and reopen your terminal."
  echo
  echo "${bold}Then verify with:${reset}"
  echo "  gau -h"
  echo "  anew -h"
  echo "  unfurl -h"
else
  echo "${bold}${green}✓ All tools verified and ready!${reset}"
fi

echo
echo "${bold}After sourcing/reopening terminal, you can run:${reset}"
echo "  ./recon-passive.sh -d target.com"
echo
echo "${bold}${green}Happy hunting! 🎯${reset}"
