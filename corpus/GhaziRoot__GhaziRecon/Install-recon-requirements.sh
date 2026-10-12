#!/usr/bin/env bash
# install-recon-requirements.sh
# Installer for web-recon toolchain (Debian/Ubuntu).
# Run on a system you control. Use with sudo.

set -euo pipefail
IFS=$'\n\t'

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run as root (or with sudo)." >&2
  echo "Usage: sudo $0" >&2
  exit 2
fi

# Basic packages (system)
APT_PKGS=(
  build-essential
  curl
  wget
  git
  jq
  nmap
  golang
  ruby-full
  python3-pip
  pandoc
  golang-go
  snapd
)

echo "[+] Updating apt and installing system packages (this may take a while)"
apt update -y
apt install -y "${APT_PKGS[@]}"

# Optional: install gobuster if not installed via apt
if ! command -v gobuster >/dev/null 2>&1; then
  echo "[i] Installing gobuster via go"
  export PATH=$PATH:$(go env GOPATH 2>/dev/null)/bin
  go install github.com/OJ/gobuster/v3@latest || true
fi

# Go tools (ProjectDiscovery, others)
export PATH=$PATH:$(go env GOPATH 2>/dev/null)/bin
if ! command -v amass >/dev/null 2>&1; then
  echo "[i] Installing amass"
  go install -v github.com/owasp/amass/v3/...@latest || true
fi

go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest || true
go install github.com/projectdiscovery/httpx/cmd/httpx@latest || true
go install github.com/lc/gau/v2/cmd/gau@latest || true
go install github.com/ffuf/ffuf@latest || true
go install github.com/tomnomnom/waybackurls@latest || true
go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest || true

# Aquatone (requires chromium or google-chrome)
if ! command -v aquatone >/dev/null 2>&1; then
  echo "[i] Installing aquatone"
  go install github.com/michenriksen/aquatone@latest || true
fi

# Install nikto, sqlmap, whatweb via apt/git
if ! command -v nikto >/dev/null 2>&1; then
  apt install -y nikto || true
fi

if ! command -v sqlmap >/dev/null 2>&1; then
  apt install -y sqlmap || true
fi

if ! command -v whatweb >/dev/null 2>&1; then
  apt install -y whatweb || true
fi

# wpscan (optional) - Ruby based
if ! command -v wpscan >/dev/null 2>&1; then
  echo "[i] Installing wpscan (Ruby gem)"
  gem install wpscan --no-document || true
fi

# SecLists
SECLISTS_DIR="/opt/SecLists"
if [[ ! -d "$SECLISTS_DIR" ]]; then
  echo "[i] Cloning SecLists to $SECLISTS_DIR"
  git clone https://github.com/danielmiessler/SecLists.git "$SECLISTS_DIR" || true
fi

# Ensure $GOPATH/bin in PATH for current shell
GOBIN=$(go env GOPATH 2>/dev/null || true)
if [[ -n "$GOBIN" ]]; then
  GOBIN="$GOBIN/bin"
  if ! grep -q "$GOBIN" /etc/profile 2>/dev/null; then
    echo "export PATH=\$PATH:$GOBIN" >> /etc/profile
  fi
fi

echo "\n[+] Installation complete. Recommended next steps:\n"
echo "1) Open a new shell or run: source /etc/profile"
echo "2) Verify tools: amass, subfinder, httpx, ffuf, gau, gobuster, nmap, nikto, sqlmap, aquatone"
echo "3) Set your preferred wordlists path (example: /opt/SecLists/Discovery/Web-Content) and update any scripts accordingly."

echo "\n[!] Note: This installer targets Debian/Ubuntu. Some tools might fail to compile depending on local Go version. If you want, I can adapt the installer for your distribution or produce a non-root (user-level) installer."

exit 0
