#!/usr/bin/env bash
set -euo pipefail

echo "[*] SpecterScan installer — Kali/Ubuntu/Debian"

# --- 0) location sanity
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# --- helper: try apt install and return 0/1
apt_install() {
  sudo apt update -y
  sudo apt install -y "$@"
}

# --- 1) packages (with special handling for wpscan)
if command -v apt >/dev/null 2>&1; then
  echo "[*] Using apt..."
  # base package list (without wpscan for now)
  BASE_PKGS=( python3 python3-venv python3-pip git curl \
    nmap whatweb nikto gobuster ffuf masscan hydra sqlmap \
    dnsutils ) # dig

  # Try installing base pkgs first
  apt_install "${BASE_PKGS[@]}"

  # Now try wpscan specially
  echo "[*] Attempting to install wpscan via apt..."
  if apt_install wpscan; then
    echo "[+] wpscan installed via apt"
  else
    echo "[!] apt couldn't find wpscan. Attempting to enable 'universe' and retry..."
    # enable universe if add-apt-repository exists
    if command -v add-apt-repository >/dev/null 2>&1; then
      sudo add-apt-repository -y universe || true
      sudo apt update -y
      if apt_install wpscan; then
        echo "[+] wpscan installed after enabling universe"
      else
        echo "[!] Still no wpscan package available. Falling back to Ruby/gem install..."
        # Install build deps for gem install
        sudo apt install -y ruby ruby-dev build-essential \
          libcurl4-openssl-dev libxml2 libxml2-dev libxslt1-dev zlib1g-dev || true
        # Install gem (may need sudo to put executable in /usr/local/bin)
        if command -v gem >/dev/null 2>&1; then
          echo "[*] Installing wpscan via gem (this may take a bit)..."
          sudo gem install wpscan || {
            echo "[!] gem install failed. As a final fallback, you can use the Docker image: docker pull wpscanteam/wpscan"
            echo "[!] Exiting with partial success."
          }
        else
          echo "[!] Ruby gem is not available after installing ruby packages. Install ruby/rubygems manually or use Docker image wpscanteam/wpscan."
        fi
      fi
    else
      echo "[!] add-apt-repository not found. Attempting gem fallback directly..."
      sudo apt install -y ruby ruby-dev build-essential \
        libcurl4-openssl-dev libxml2 libxml2-dev libxslt1-dev zlib1g-dev || true
      if command -v gem >/dev/null 2>&1; then
        echo "[*] Installing wpscan via gem..."
        sudo gem install wpscan || {
          echo "[!] gem install failed. Consider installing docker and running wpscanteam/wpscan docker image."
        }
      else
        echo "[!] gem not available — please install ruby/rubygems or use Docker image: docker pull wpscanteam/wpscan"
      fi
    fi
  fi

else
  echo "[!] apt not found. Please install deps manually for your distro."
  exit 1
fi

# --- 2) optional venv (comment out if you prefer system python)
if [ ! -d ".venv" ]; then
  echo "[*] Creating Python venv ./.venv"
  python3 -m venv .venv
fi
echo "[*] Upgrading pip"
. .venv/bin/activate
pip install --upgrade pip

# --- 3) wordlists (curated SecLists snippets)
mkdir -p wordlists
download() {
  local out="$1" url="$2"
  if [ -s "wordlists/$out" ]; then
    echo "[=] wordlists/$out exists"
  else
    echo "[*] downloading $out"
    curl -sSL -o "wordlists/$out" "$url"
  fi
}

download "subdomains-top1k.txt" "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1k.txt"
download "usernames-top1k.txt"  "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Usernames/top-usernames-shortlist.txt"
download "passwords-10k.txt"    "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10k-most-common.txt"

echo "[*] Wordlists ready:"
ls -lh wordlists

# --- 4) final tips
echo
echo "[+] Install complete."
echo "   • Activate venv:   source .venv/bin/activate"
echo "   • Enable aggressive: export ADVSCAN_ALLOW_AGGRESSIVE=1"
echo "   • Run:              python3 specterscan.py"
