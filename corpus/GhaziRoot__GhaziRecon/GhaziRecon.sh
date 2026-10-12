#!/usr/bin/env bash

echo "__| |___________________________________________| |__"
echo "__   ___________________________________________   __"
echo "  | |                                           | |  "
echo "  | | ██████╗ ██╗  ██╗ █████╗ ███████╗██╗       | |  "
echo "  | |██╔════╝ ██║  ██║██╔══██╗╚══███╔╝██║       | |  "
echo "  | |██║  ███╗███████║███████║  ███╔╝ ██║       | |  "
echo "  | |██║   ██║██╔══██║██╔══██║ ███╔╝  ██║       | |  "
echo "  | |╚██████╔╝██║  ██║██║  ██║███████╗██║       | |  "
echo "  | | ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝       | |  "
echo "  | |                                           | |  "
echo "  | |██████╗ ███████╗ ██████╗ ██████╗ ███╗   ██╗| |  "
echo "  | |██╔══██╗██╔════╝██╔════╝██╔═══██╗████╗  ██║| |  "
echo "  | |██████╔╝█████╗  ██║     ██║   ██║██╔██╗ ██║| |  "
echo "  | |██╔══██╗██╔══╝  ██║     ██║   ██║██║╚██╗██║| |  "
echo "  | |██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║| |  "
echo "  | |╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝| |  "
echo "__| |___________________________________________| |__"
echo "__   ___________________________________________   __"
echo "  | |                                           | |  "


set -euo pipefail
IFS=$'\n\t'

#########################
# Configuration & usage
#########################

USAGE="Usage: $0 -d <domain-or-target> [-o output_dir] [-e exploit]
  -d target domain or file with targets (required)
  -o output directory (default: ./recon-<target>-<timestamp>)
  -e enable optional intrusive modules (sqlmap, nikto aggressive) (default: off)
  -t threads for parallel tools (default: 20)
Example: $0 -d example.com -o /tmp/recon -t 50\n"

TARGET=""
OUTDIR=""
ENABLE_EXPLOITS=false
THREADS=20

while getopts ":d:o:et:" opt; do
  case ${opt} in
    d) TARGET="$OPTARG" ;;
    o) OUTDIR="$OPTARG" ;;
    e) ENABLE_EXPLOITS=true ;;
    t) THREADS="$OPTARG" ;;
    \?) echo "Invalid option: -$OPTARG" >&2; echo "$USAGE"; exit 1 ;;
    :) echo "Option -$OPTARG requires an argument." >&2; echo "$USAGE"; exit 1 ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "Target required.\n$USAGE"
  exit 1
fi

TS=$(date +%Y%m%d_%H%M%S)
if [[ -z "$OUTDIR" ]]; then
  SAFE_TARGET=$(echo "$TARGET" | sed 's/[^a-zA-Z0-9]/_/g' | cut -c1-60)
  OUTDIR="./recon_${SAFE_TARGET}_${TS}"
fi
mkdir -p "$OUTDIR"
mkdir -p "$OUTDIR/raw"
mkdir -p "$OUTDIR/subdomains"
mkdir -p "$OUTDIR/hosts"
mkdir -p "$OUTDIR/http"
mkdir -p "$OUTDIR/screenshots"
mkdir -p "$OUTDIR/fuzz"
mkdir -p "$OUTDIR/scanners"
mkdir -p "$OUTDIR/reports"

LOGFILE="$OUTDIR/recon.log"
exec > >(tee -a "$LOGFILE") 2>&1

echo "[+] Recon started: $(date)"
echo "[+] Target: $TARGET"
echo "[+] Output: $OUTDIR"
echo "[+] Threads: $THREADS"
[ "$ENABLE_EXPLOITS" = true ] && echo "[!] Exploits enabled: ON" || echo "[i] Exploits enabled: OFF"

#########################
# Check prerequisites
#########################
REQUIRED=(nmap amass subfinder httpx whatweb ffuf gobuster aquatone gau sqlmap nikto jq)
MISSING=()
for cmd in "nmap" "amass" "subfinder" "httpx" "whatweb" "ffuf" "gobuster" "aquatone" "gau" "sqlmap" "nikto" "jq"; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    MISSING+=("$cmd")
  fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "[!] Warning: The following tools are not in PATH: ${MISSING[*]}"
  echo "[i] The script will try best-effort to continue with available tools.\n"
fi

#########################
# Helper functions
#########################

join_unique() {
  sort -u | tee "$1"
}

timestamped() {
  echo "[$(date +'%H:%M:%S')] $*"
}

# safe-run: run command but continue on failure (useful for 3rd-party tools)
safe_run() {
  timestamped "RUN: $*"
  if ! eval "$*"; then
    timestamped "WARN: command failed: $*"
  fi
}

#########################
# 1) Subdomain discovery (passive -> active)
#########################
SUB_ALL="$OUTDIR/subdomains/all_subs.txt"
> "$SUB_ALL"

if command -v amass >/dev/null 2>&1; then
  timestamped "Running amass enum (passive + active)"
  safe_run "amass enum -passive -d '$TARGET' -o '$OUTDIR/subdomains/amass_passive.txt' || true"
  safe_run "amass enum -d '$TARGET' -o '$OUTDIR/subdomains/amass_active.txt' || true"
fi

if command -v subfinder >/dev/null 2>&1; then
  timestamped "Running subfinder (passive)"
  safe_run "subfinder -d '$TARGET' -silent -o '$OUTDIR/subdomains/subfinder.txt' || true"
fi

# crt.sh via curl (fallback)
timestamped "Querying crt.sh for certificates"
safe_run "curl -s 'https://crt.sh/?q=%25.$TARGET&output=json' > '$OUTDIR/subdomains/crt_sh.json' || true"
if [[ -s "$OUTDIR/subdomains/crt_sh.json" ]]; then
  jq -r '.[].name_value' "$OUTDIR/subdomains/crt_sh.json" 2>/dev/null | sed 's/\*\.//g' | sort -u >> "$SUB_ALL" || true
fi

# collect amass/subfinder outputs
for f in "$OUTDIR/subdomains"/*amass*.txt "$OUTDIR/subdomains/subfinder.txt"; do
  [[ -f "$f" ]] || continue
  cat "$f" >> "$SUB_ALL"
done

# dedupe and clean
cat "$SUB_ALL" | sed 's/\r//g' | sed 's/^\.*//g' | awk '{print tolower($0)}' | sort -u > "$OUTDIR/subdomains/subs_raw.txt"

# if no subs found and target looks like domain, include target
if [[ ! -s "$OUTDIR/subdomains/subs_raw.txt" ]]; then
  echo "$TARGET" > "$OUTDIR/subdomains/subs_raw.txt"
fi

#########################
# 2) Probe for live HTTP hosts
#########################
LIVE_HOSTS="$OUTDIR/hosts/live_hosts.txt"
> "$LIVE_HOSTS"

if command -v httpx >/dev/null 2>&1; then
  timestamped "Probing HTTP(s) with httpx"
  safe_run "cat '$OUTDIR/subdomains/subs_raw.txt' | httpx -silent -threads $THREADS -o '$OUTDIR/hosts/httpx_output.txt' -status-code -title -ip -cdn || true"
  if [[ -s "$OUTDIR/hosts/httpx_output.txt" ]]; then
    cut -f1 -d ' ' "$OUTDIR/hosts/httpx_output.txt" | sort -u > "$LIVE_HOSTS"
  fi
else
  timestamped "httpx not found: attempting curl-based probe"
  while read -r host; do
    if curl -sI --connect-timeout 5 "http://$host" >/dev/null 2>&1 || curl -sI --connect-timeout 5 "https://$host" >/dev/null 2>&1; then
      echo "$host" >> "$LIVE_HOSTS"
    fi
  done < "$OUTDIR/subdomains/subs_raw.txt"
  sort -u "$OUTDIR/hosts/live_hosts.txt" -o "$OUTDIR/hosts/live_hosts.txt" || true
fi

# fallback: if live hosts empty, use subs_raw
if [[ ! -s "$LIVE_HOSTS" ]]; then
  cp "$OUTDIR/subdomains/subs_raw.txt" "$LIVE_HOSTS"
fi

#########################
# 3) Nmap port & service scan for each live host (fast then deep)
#########################
NMAP_DIR="$OUTDIR/scanners/nmap"
mkdir -p "$NMAP_DIR"

timestamped "Running nmap quick port scan (top ports)"
while read -r host; do
  SAFE_HOST=$(echo "$host" | sed 's/[^a-zA-Z0-9\.\-]/_/g')
  safe_run "nmap -sS -Pn --top-ports 100 -oA '$NMAP_DIR/$SAFE_HOST-top' $host || true"
done < "$LIVE_HOSTS"

# deeper scan for hosts that have common HTTP ports
timestamped "Running targeted nmap service/version scan on discovered HTTP ports"
while read -r host; do
  SAFE_HOST=$(echo "$host" | sed 's/[^a-zA-Z0-9\.\-]/_/g')
  safe_run "nmap -sV -p 80,443,8080,8443 -oA '$NMAP_DIR/$SAFE_HOST-http' $host || true"
done < "$LIVE_HOSTS"

#########################
# 4) URL harvesting (gau / waybackurls / crawling)
#########################
URLS_ALL="$OUTDIR/http/urls_all.txt"
> "$URLS_ALL"

if command -v gau >/dev/null 2>&1; then
  timestamped "Gathering historical URLs (gau)"
  safe_run "cat '$OUTDIR/subdomains/subs_raw.txt' | xargs -I % -P $THREADS sh -c 'gau % >> "$OUTDIR/http/gau_raw.txt"' || true"
fi

if command -v waybackurls >/dev/null 2>&1; then
  timestamped "Gathering waybackurls"
  safe_run "cat '$OUTDIR/subdomains/subs_raw.txt' | waybackurls >> '$OUTDIR/http/wayback_raw.txt' || true"
fi

# combine and filter
for f in "$OUTDIR/http/gau_raw.txt" "$OUTDIR/http/wayback_raw.txt"; do
  [[ -f "$f" ]] || continue
  cat "$f" >> "$URLS_ALL"
done

# basic URL sanitation
if [[ -s "$URLS_ALL" ]]; then
  cat "$URLS_ALL" | sort -u > "$OUTDIR/http/urls_sorted.txt"
else
  # fallback: probe homepage paths
  while read -r host; do
    echo "http://$host/" >> "$OUTDIR/http/urls_sorted.txt"
    echo "https://$host/" >> "$OUTDIR/http/urls_sorted.txt"
  done < "$LIVE_HOSTS"
fi

#########################
# 5) Fingerprinting & tech discovery
#########################
TECH_DIR="$OUTDIR/scanners/tech"
mkdir -p "$TECH_DIR"

if command -v whatweb >/dev/null 2>&1; then
  timestamped "Running whatweb against live hosts"
  while read -r host; do
    safe_run "whatweb -v --log-verbose='$TECH_DIR/whatweb_${host}.log' https://$host || true"
  done < "$LIVE_HOSTS"
fi

#########################
# 6) Screenshot collection (aquatone) — visual triage
#########################
if command -v aquatone >/dev/null 2>&1; then
  if [[ -s "$OUTDIR/hosts/httpx_output.txt" ]]; then
    timestamped "Generating aquatone screenshots (from httpx list)"
    safe_run "cat '$OUTDIR/hosts/httpx_output.txt' | awk '{print $1}' | aquatone -out '$OUTDIR/screenshots' || true"
  else
    timestamped "Aquatone: using live hosts list"
    cat "$LIVE_HOSTS" | sed 's#^#https://#' | aquatone -out "$OUTDIR/screenshots" || true
  fi
fi

#########################
# 7) Directory/file brute force (ffuf) — conservative default (improved)
#########################
# Priority: 1) GH_WORDLIST env var  2) common system paths  3) /opt/SecLists  4) download SecLists common.txt to OUTDIR  5) fallback builtin list
WL=""

# 1) allow user override via env
if [[ -n "${GH_WORDLIST:-}" ]] && [[ -f "${GH_WORDLIST}" ]]; then
  WL="${GH_WORDLIST}"
fi

# 2) common system locations
if [[ -z "$WL" ]]; then
  WORDLISTS=(/usr/share/wordlists/dirb/common.txt /usr/share/seclists/Discovery/Web-Content/common.txt /usr/share/wordlists/seclists/Discovery/Web-Content/common.txt)
  for w in "${WORDLISTS[@]}"; do
    [[ -f "$w" ]] && { WL="$w"; break; }
  done
fi

# 3) check /opt/SecLists (user might have cloned SecLists there)
if [[ -z "$WL" ]] && [[ -d "/opt/SecLists" ]]; then
  if [[ -f "/opt/SecLists/Discovery/Web-Content/common.txt" ]]; then
    WL="/opt/SecLists/Discovery/Web-Content/common.txt"
  fi
fi

# 4) attempt to download a copy into OUTDIR/wordlists if nothing found
if [[ -z "$WL" ]]; then
  mkdir -p "$OUTDIR/wordlists"
  DL_TARGET="$OUTDIR/wordlists/common.txt"
  if command -v curl >/dev/null 2>&1; then
    timestamped "No wordlist found locally — attempting to download SecLists common.txt to $DL_TARGET"
    if curl -fsSL "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt" -o "$DL_TARGET"; then
      WL="$DL_TARGET"
    else
      timestamped "Failed to download with curl."
    fi
  elif command -v wget >/dev/null 2>&1; then
    timestamped "No wordlist found locally — attempting to download SecLists common.txt to $DL_TARGET"
    if wget -q -O "$DL_TARGET" "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt"; then
      WL="$DL_TARGET"
    else
      timestamped "Failed to download with wget."
    fi
  fi
fi

# 5) fallback: tiny builtin list (safe conservative)
if [[ -z "$WL" ]]; then
  timestamped "No external wordlist available — using small builtin fallback (conservative)."
  BUILTIN="$OUTDIR/wordlists/builtin_common.txt"
  cat > "$BUILTIN" <<'EOF'
index.html
index.php
login
admin
admin.php
robots.txt
sitemap.xml
uploads
images
assets
css
js
api
config
README.md
EOF
  WL="$BUILTIN"
fi

# run ffuf if available
if [[ -n "$WL" ]] && command -v ffuf >/dev/null 2>&1; then
  timestamped "Running ffuf on live hosts (wordlist: $WL)"
  while read -r host; do
    # prefer https but allow http fallback via ffuf's -mc handling if needed
    URL="https://$host"
    OUTF="$OUTDIR/fuzz/ffuf_${host//[^a-zA-Z0-9]/_}.json"
    safe_run "ffuf -u '$URL/FUZZ' -w '$WL' -t $THREADS -mc 200,301,302,403 -o '$OUTF' -of json || true"
  done < "$LIVE_HOSTS"
else
  timestamped "Skipping ffuf stage: wordlist not found or ffuf not installed."
fi

#########################
# 8) Basic vulnerability scanners (non-invasive by default)
#########################
if command -v nikto >/dev/null 2>&1; then
  timestamped "Running nikto light scans on http hosts"
  while read -r host; do
    safe_run "nikto -h https://$host -o '$OUTDIR/scanners/nikto_${host//[^a-zA-Z0-9]/_}.txt' -Format txt || true"
  done < "$LIVE_HOSTS"
fi

if [[ "$ENABLE_EXPLOITS" = true ]]; then
  timestamped "[!] Exploit-mode: running sqlmap in safe-autonomous mode (user enabled)"
  if command -v sqlmap >/dev/null 2>&1 && [[ -s "$OUTDIR/http/urls_sorted.txt" ]]; then
    head -n 200 "$OUTDIR/http/urls_sorted.txt" | grep -E "(\?|=)" | while read -r u; do
      SAFE_FN="$OUTDIR/scanners/sqlmap_$(echo "$u" | md5sum | cut -d' ' -f1).txt"
      safe_run "sqlmap -u \"$u\" --batch --level=1 --risk=1 -o $SAFE_FN || true"
    done
  fi
fi

#########################
# 9) Collect & normalize artifacts
#########################
timestamped "Collecting artifacts and normalizing"
# consolidate lists
for f in "$OUTDIR/subdomains/subs_raw.txt" "$LIVE_HOSTS" "$OUTDIR/http/urls_sorted.txt"; do
  [[ -f "$f" ]] && cat "$f" >> "$OUTDIR/raw/all_artifacts_combined.txt"
done
sort -u "$OUTDIR/raw/all_artifacts_combined.txt" -o "$OUTDIR/raw/all_artifacts_combined.txt" || true

# collect ffuf/nmap outputs
find "$OUTDIR" -type f -name "*.txt" -o -name "*.log" -o -name "*.json" > "$OUTDIR/raw/file_manifest.txt"

#########################
# 10) Generate final markdown report
#########################
REPORT_MD="$OUTDIR/reports/recon_report_${TS}.md"
{
  echo "# Recon Report for $TARGET"
  echo "Generated: $(date -u)"
  echo ""
  echo "## Summary"
  echo "- Target: $TARGET"
  echo "- Output directory: $OUTDIR"
  echo "- Threads: $THREADS"
  echo "- Exploit-mode: $ENABLE_EXPLOITS"
  echo ""
  echo "## Hosts & Subdomains (unique)"
  echo '```'
  [[ -f "$OUTDIR/subdomains/subs_raw.txt" ]] && cat "$OUTDIR/subdomains/subs_raw.txt" || true
  echo '```'
  echo ""
  echo "## Live HTTP hosts"
  echo '```'
  [[ -f "$LIVE_HOSTS" ]] && cat "$LIVE_HOSTS" || true
  echo '```'
  echo ""
  echo "## Top Nmap findings (first 100 lines from nmap raw outputs)"
  echo '```'
  for n in $(ls -1 "$NMAP_DIR" 2>/dev/null || true); do
    echo "--- $n ---"
    head -n 100 "$NMAP_DIR/$n.nmap" 2>/dev/null || true
  done
  echo '```'
  echo ""
  echo "## Notable URLs (sample)"
  echo '```'
  head -n 200 "$OUTDIR/http/urls_sorted.txt" 2>/dev/null || true
  echo '```'
  echo ""
  echo "## FFUF Findings (summaries)"
  echo '```'
  for f in "$OUTDIR/fuzz"/*.json 2>/dev/null; do
    [[ -f "$f" ]] || continue
    jq -r '.results[] | "[" + (.status) + "] " + .url' "$f" 2>/dev/null | head -n 50 || true
  done
  echo '```'
  echo ""
  echo "## Scanners outputs (nikto / sqlmap summaries)"
  echo '```'
  for s in "$OUTDIR/scanners"/* 2>/dev/null; do
    [[ -f "$s" ]] || continue
    echo "--- $(basename "$s") ---"
    head -n 40 "$s" || true
  done
  echo '```'
  echo ""
  echo "## Screenshots"
  if ls "$OUTDIR/screenshots" 2>/dev/null | grep -q .; then
    echo "Screenshots saved in ./screenshots/ (take a look)"
  else
    echo "No screenshots generated or aquatone missing."
  fi
  echo ""
  echo "## Raw manifest"
  echo '```'
  cat "$OUTDIR/raw/file_manifest.txt" 2>/dev/null || true
  echo '```'
  echo ""
  echo "## Notes & Next Steps"
  echo "- Validate findings manually."
  echo "- Prioritize sensitive endpoints (login, admin panels, upload)."
  echo "- If authorized, run deeper scans during permitted windows."
} > "$REPORT_MD"

# also produce a short HTML using pandoc if available
if command -v pandoc >/dev/null 2>&1; then
  timestamped "Converting markdown report to HTML with pandoc"
  safe_run "pandoc '$REPORT_MD' -o '$OUTDIR/reports/recon_report_${TS}.html' || true"
fi

#########################
# Finish
#########################

echo "[+] Recon finished: $(date)"
echo "[+] Final report: $REPORT_MD"

echo "[!] Reminder: Always have explicit permission to test targets. This script includes optional intrusive steps only when -e is provided."

exit 0
