#!/usr/bin/env bash
set -euo pipefail

# recon-ultimate.sh v1 — Combined passive + active reconnaissance
# Usage: ./recon-ultimate.sh -d domain [-o ~/bugbounty/recon] [-w /path/to/wordlist] [-t THREADS] [-j JOBS] [-m MODE]

DOMAIN=""
OUT_BASE="${HOME}/bugbounty/recon"
WORDLIST=""
THREADS=15
PARALLEL_JOBS=5
MODE=""  # passive, active, or full

usage() {
  cat <<EOF
Usage: $0 -d domain [-o outbase] [-w wordlist] [-t threads] [-j jobs] [-m mode]
  -d domain    : domain to run recon on (required)
  -o outbase   : base output dir (default: ${OUT_BASE})
  -w wordlist  : optional ffuf wordlist for directory fuzzing
  -t threads   : threads for active tools (default: ${THREADS})
  -j jobs      : parallel jobs for waybackurls (default: ${PARALLEL_JOBS})
  -m mode      : recon mode (passive|active|full) - will prompt if not specified

Modes:
  passive : Subdomain enum + wayback URLs + pattern matching (NO target contact)
  active  : Passive + HTTPx probing + Nuclei scanning (sends requests to target)
  full    : Active + optional FFUF directory fuzzing (most comprehensive)
EOF
  exit 1
}

while getopts "d:o:w:t:j:m:h" opt; do
  case "${opt}" in
    d) DOMAIN="${OPTARG}";;
    o) OUT_BASE="${OPTARG}";;
    w) WORDLIST="${OPTARG}";;
    t) THREADS="${OPTARG}";;
    j) PARALLEL_JOBS="${OPTARG}";;
    m) MODE="${OPTARG}";;
    h|*) usage;;
  esac
done

if [[ -z "$DOMAIN" ]]; then
  echo

# Check for required core tools
echo "${bold}${cyan}Checking required tools...${reset}"
MISSING_TOOLS=()

if ! command -v subfinder >/dev/null 2>&1; then
  MISSING_TOOLS+=("subfinder")
fi

if ! command -v waybackurls >/dev/null 2>&1; then
  MISSING_TOOLS+=("waybackurls")
fi

if [[ "$MODE" == "active" ]] || [[ "$MODE" == "full" ]]; then
  if ! command -v httpx >/dev/null 2>&1; then
    MISSING_TOOLS+=("httpx")
  fi
  if ! command -v nuclei >/dev/null 2>&1; then
    MISSING_TOOLS+=("nuclei")
  fi
fi

if [[ "$MODE" == "full" ]] && [[ -n "$WORDLIST" ]]; then
  if ! command -v ffuf >/dev/null 2>&1; then
    MISSING_TOOLS+=("ffuf")
  fi
fi

if [[ ${#MISSING_TOOLS[@]} -gt 0 ]]; then
  echo "${bold}${red}ERROR: Required tools not found:${reset}"
  for tool in "${MISSING_TOOLS[@]}"; do
    echo "  ${red}✗${reset} $tool"
  done
  echo
  echo "${yellow}Run the installer:${reset}"
  echo "  ./install-recon-tools.sh"
  echo
  exit 1
else
  echo "${green}✓ All required tools found${reset}"
fi
echo "ERROR: domain is required."
  usage
fi

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
OUTDIR="${OUT_BASE}/${DOMAIN}/${TIMESTAMP}"
mkdir -p "$OUTDIR"

# Enable logging to file
LOG_FILE="${OUTDIR}/run.log"
exec > >(tee "$LOG_FILE") 2>&1
echo "Logging to: $LOG_FILE"
echo

# color helpers
if command -v tput >/dev/null 2>&1; then
  bold="$(tput bold)"; red="$(tput setaf 1)"; green="$(tput setaf 2)"; yellow="$(tput setaf 3)"
  cyan="$(tput setaf 6)"; magenta="$(tput setaf 5)"; reset="$(tput sgr0)"
else
  bold=""; red=""; green=""; yellow=""; cyan=""; magenta=""; reset=""
fi

# Banner
cat <<'BANNER'
   ___  _____ _____ ____  ____  ____  _   _ _   _ _   _ _____ 
  / _ \|_   _|_   _|___ \|  _ \|  _ \| | | | | | | \ | |_   _|
 | | | | | |   | |   __) | |_) | |_) | |_| | | | |  \| | | |  
 | |_| | | |   | |  |__ <|  _ <|  _ <|  _  | |_| | |\  | | |  
  \___/  |_|   |_|  |___/|_| \_\_| \_\_| |_|\___/|_| \_| |_|  
                                                                
                  Hunt Smarter, Not Harder
BANNER

echo "${bold}${cyan}════════════════════════════════════════════════${reset}"
echo

# Interactive mode selection if not specified
if [[ -z "$MODE" ]]; then
  echo "${bold}${cyan}Select reconnaissance mode:${reset}"
  echo
  echo "  ${bold}1)${reset} ${green}Passive${reset}  - Subdomain enum + wayback URLs + pattern matching"
  echo "               ${magenta}✓ 100% stealth - zero target contact${reset}"
  echo "               ${magenta}✓ Safe for any bug bounty program${reset}"
  echo
  echo "  ${bold}2)${reset} ${yellow}Active${reset}   - Passive + live host probing + vulnerability scanning"
  echo "               ${red}⚠ Sends requests to target${reset}"
  echo "               ${yellow}⚠ Only use if program allows active scanning${reset}"
  echo
  echo "  ${bold}3)${reset} ${red}Full${reset}     - Active + directory fuzzing (most comprehensive)"
  echo "               ${red}⚠ Very noisy - high request volume${reset}"
  echo "               ${red}⚠ May trigger WAF/IDS alerts${reset}"
  echo
  printf "${bold}Enter your choice [1-3] (default: 1/passive):${reset} "
  read -r choice
  
  case "$choice" in
    1|"") MODE="passive";;
    2) MODE="active";;
    3) MODE="full";;
    *) echo "${yellow}Invalid choice. Defaulting to passive mode.${reset}"; MODE="passive";;
  esac
  echo
fi

# Normalize mode
MODE=$(echo "$MODE" | tr '[:upper:]' '[:lower:]')

# Display run summary
echo "${bold}${cyan}Run Configuration:${reset}"
echo "  Domain     : ${bold}${DOMAIN}${reset}"
echo "  Output dir : ${bold}${OUTDIR}${reset}"
echo "  Mode       : ${bold}${MODE}${reset}"
if [[ "$MODE" == "active" ]] || [[ "$MODE" == "full" ]]; then
  echo "  Threads    : ${bold}${THREADS}${reset}"
  echo "  Parallel   : ${bold}${PARALLEL_JOBS}${reset}"
fi
if [[ "$MODE" == "full" ]] && [[ -n "$WORDLIST" ]]; then
  echo "  FFUF wordlist: ${bold}${WORDLIST}${reset}"
elif [[ "$MODE" == "full" ]]; then
  echo "  FFUF       : ${bold}disabled (no wordlist)${reset}"
fi
echo

# Mode-specific warnings
case "$MODE" in
  passive)
    echo "${bold}${green}✓ PASSIVE MODE${reset} - No requests will be sent to ${DOMAIN}"
    ;;
  active)
    echo "${bold}${yellow}⚠ ACTIVE MODE${reset} - Will probe live hosts and run vulnerability scans"
    echo "${yellow}  Ensure this is authorized and within bug bounty scope!${reset}"
    ;;
  full)
    echo "${bold}${red}⚠ FULL MODE${reset} - Will run comprehensive active scanning including fuzzing"
    echo "${red}  This is NOISY and may trigger security alerts!${reset}"
    echo "${red}  Only use on targets that explicitly allow this level of scanning.${reset}"
    ;;
esac
echo

# Show toolchain status based on mode
echo "${bold}${cyan}Toolchain Status (Mode: ${MODE}):${reset}"

show_ver() {
  cmd=$1; verflag=${2:--h}
  if command -v "$cmd" >/dev/null 2>&1; then
    printf "  %-12s : " "$cmd"
    if output="$($cmd ${verflag} 2>&1 | head -n1 | cut -c1-50)"; then
      echo "${green}${output}${reset}"
    else
      echo "${yellow}installed${reset}"
    fi
  else
    printf "  %-12s : ${red}missing${reset}\n" "$cmd"
  fi
}

# Always show passive tools
show_ver subfinder -version
show_ver waybackurls
if [[ "$MODE" == "passive" ]]; then
  show_ver assetfinder
  show_ver amass -version
  show_ver gau
  show_ver gf
fi

# Show active tools for active/full modes
if [[ "$MODE" == "active" ]] || [[ "$MODE" == "full" ]]; then
  show_ver assetfinder
  show_ver amass -version
  show_ver gau
  show_ver httpx -version
  show_ver nuclei -version
  show_ver gf
fi

# Show fuzzing tools for full mode
if [[ "$MODE" == "full" ]]; then
  show_ver ffuf
fi

echo

# Show planned steps based on mode
echo "${bold}${cyan}Planned Steps (Mode: ${MODE}):${reset}"

case "$MODE" in
  passive)
    echo "  ${bold}PHASE 1: PASSIVE RECONNAISSANCE${reset}"
    echo "    1) Subdomain enumeration (subfinder)"
    step_count=2
    if command -v assetfinder >/dev/null 2>&1; then
      echo "    ${step_count}) Additional subdomains (assetfinder)"
      ((step_count++))
    fi
    if command -v amass >/dev/null 2>&1; then
      echo "    ${step_count}) Deep enumeration (amass passive)"
      ((step_count++))
    fi
    echo "    ${step_count}) Wayback Machine URLs (waybackurls)"
    ((step_count++))
    if command -v gau >/dev/null 2>&1; then
      echo "    ${step_count}) Additional archived URLs (gau)"
      ((step_count++))
    fi
    echo "    ${step_count}) Pattern filtering (gf)"
    ;;
  active)
    echo "  ${bold}PHASE 1: PASSIVE RECONNAISSANCE${reset}"
    echo "    1) Subdomain enumeration (subfinder)"
    step_count=2
    if command -v assetfinder >/dev/null 2>&1; then
      echo "    ${step_count}) Additional subdomains (assetfinder)"
      ((step_count++))
    fi
    if command -v amass >/dev/null 2>&1; then
      echo "    ${step_count}) Deep enumeration (amass passive)"
      ((step_count++))
    fi
    echo "    ${step_count}) Wayback Machine URLs (waybackurls)"
    ((step_count++))
    if command -v gau >/dev/null 2>&1; then
      echo "    ${step_count}) Additional archived URLs (gau)"
      ((step_count++))
    fi
    echo "    ${step_count}) Pattern filtering (gf)"
    ((step_count++))
    echo "  ${bold}PHASE 2: ACTIVE RECONNAISSANCE${reset}"
    echo "    ${step_count}) Live host probing (httpx)"
    ((step_count++))
    echo "    ${step_count}) Vulnerability scanning (nuclei)"
    ((step_count++))
    echo "    ${step_count}) Pattern matching on live hosts"
    ;;
  full)
    echo "  ${bold}PHASE 1: PASSIVE RECONNAISSANCE${reset}"
    echo "    1) Subdomain enumeration (subfinder)"
    step_count=2
    if command -v assetfinder >/dev/null 2>&1; then
      echo "    ${step_count}) Additional subdomains (assetfinder)"
      ((step_count++))
    fi
    if command -v amass >/dev/null 2>&1; then
      echo "    ${step_count}) Deep enumeration (amass passive)"
      ((step_count++))
    fi
    echo "    ${step_count}) Wayback Machine URLs (waybackurls)"
    ((step_count++))
    if command -v gau >/dev/null 2>&1; then
      echo "    ${step_count}) Additional archived URLs (gau)"
      ((step_count++))
    fi
    echo "    ${step_count}) Pattern filtering (gf)"
    ((step_count++))
    echo "  ${bold}PHASE 2: ACTIVE RECONNAISSANCE${reset}"
    echo "    ${step_count}) Live host probing (httpx)"
    ((step_count++))
    echo "    ${step_count}) Vulnerability scanning (nuclei)"
    ((step_count++))
    echo "    ${step_count}) Pattern matching on live hosts"
    ((step_count++))
    echo "  ${bold}PHASE 3: DIRECTORY FUZZING${reset}"
    if [[ -n "$WORDLIST" ]]; then
      echo "    ${step_count}) Directory fuzzing (ffuf)"
    else
      echo "    ${step_count}) Directory fuzzing (ffuf) - ${yellow}SKIPPED: no wordlist${reset}"
    fi
    ;;
esac

echo

printf "${bold}Press Enter to start${reset} (or Ctrl-C to cancel) "
read -r _dummy
echo

# timing helpers
RUN_START_TS=$(date +%s)
step_start_ts=0
step_end_ts=0
print_elapsed() {
  local secs=$1
  local h=$((secs/3600))
  local m=$(( (secs%3600)/60 ))
  local s=$((secs%60))
  if (( h>0 )); then
    printf "%dh%02dm%02ds" $h $m $s
  elif (( m>0 )); then
    printf "%dm%02ds" $m $s
  else
    printf "%ds" $s
  fi
}

step_num=0
total_steps=0
step_done() {
  step_end_ts=$(date +%s)
  local duration=$((step_end_ts - step_start_ts))
  local elapsed=$((step_end_ts - RUN_START_TS))
  step_num=$((step_num+1))
  local pct=$(( (step_num * 100) / total_steps ))
  echo "    ${yellow}Step ${step_num}/${total_steps} completed in $(print_elapsed $duration). Overall: ${pct}% done. Elapsed: $(print_elapsed $elapsed)${reset}"
  echo
}

# Calculate total steps based on mode
case "$MODE" in
  passive)
    total_steps=5  # subfinder, assetfinder/amass, wayback, gau, patterns
    if command -v assetfinder >/dev/null 2>&1; then ((total_steps++)); fi
    if command -v amass >/dev/null 2>&1; then ((total_steps++)); fi
    if command -v gau >/dev/null 2>&1; then ((total_steps++)); fi
    ;;
  active)
    total_steps=8  # passive + httpx + nuclei + gf
    if command -v assetfinder >/dev/null 2>&1; then ((total_steps++)); fi
    if command -v amass >/dev/null 2>&1; then ((total_steps++)); fi
    if command -v gau >/dev/null 2>&1; then ((total_steps++)); fi
    ;;
  full)
    total_steps=9  # active + ffuf
    if command -v assetfinder >/dev/null 2>&1; then ((total_steps++)); fi
    if command -v amass >/dev/null 2>&1; then ((total_steps++)); fi
    if command -v gau >/dev/null 2>&1; then ((total_steps++)); fi
    if [[ -n "$WORDLIST" ]]; then ((total_steps++)); fi
    ;;
esac

# ============================================================
# PHASE 1: PASSIVE RECONNAISSANCE (ALL MODES)
# ============================================================

echo "${bold}${cyan}═══════════════════════════════════════════════${reset}"
echo "${bold}${cyan}  PHASE 1: PASSIVE RECONNAISSANCE${reset}"
echo "${bold}${cyan}═══════════════════════════════════════════════${reset}"
echo

# ---------- Step: Subfinder ----------
echo "${bold}${cyan}[${step_num}/${total_steps}] Subdomain enumeration (subfinder)${reset}"
step_start_ts=$(date +%s)
SUBS_SUBFINDER="$OUTDIR/subdomains_subfinder.txt"
SUBS_ALL="$OUTDIR/subdomains_all.txt"
subfinder -d "$DOMAIN" -silent -o "$SUBS_SUBFINDER" -all 2>/dev/null || subfinder -d "$DOMAIN" -silent -o "$SUBS_SUBFINDER" || true
cat "$SUBS_SUBFINDER" 2>/dev/null | sort -u > "$SUBS_ALL" || touch "$SUBS_ALL"
step_done

# ---------- Step: Assetfinder (if available) ----------
if command -v assetfinder >/dev/null 2>&1; then
  echo "${bold}${cyan}[${step_num}/${total_steps}] Additional subdomains (assetfinder)${reset}"
  step_start_ts=$(date +%s)
  ASSET_SUBS="$OUTDIR/subdomains_assetfinder.txt"
  assetfinder --subs-only "$DOMAIN" 2>/dev/null | sort -u > "$ASSET_SUBS" || touch "$ASSET_SUBS"
  if [[ -s "$ASSET_SUBS" ]]; then
    cat "$ASSET_SUBS" >> "$SUBS_ALL"
    sort -u "$SUBS_ALL" -o "$SUBS_ALL"
  fi
  step_done
fi

# ---------- Step: Amass (if available) ----------
if command -v amass >/dev/null 2>&1; then
  echo "${bold}${cyan}[${step_num}/${total_steps}] Deep enumeration (amass passive)${reset}"
  step_start_ts=$(date +%s)
  AMASS_SUBS="$OUTDIR/subdomains_amass.txt"
  amass enum -passive -d "$DOMAIN" -o "$AMASS_SUBS" 2>/dev/null || touch "$AMASS_SUBS"
  if [[ -s "$AMASS_SUBS" ]]; then
    cat "$AMASS_SUBS" >> "$SUBS_ALL"
    sort -u "$SUBS_ALL" -o "$SUBS_ALL"
  fi
  step_done
fi

# ---------- Step: Waybackurls ----------
echo "${bold}${cyan}[${step_num}/${total_steps}] Wayback Machine URLs (waybackurls)${reset}"
step_start_ts=$(date +%s)
WAYBACK="$OUTDIR/urls_wayback.txt"
URLS_ALL="$OUTDIR/urls_all.txt"

if [[ -s "$SUBS_ALL" ]]; then
  if command -v parallel >/dev/null 2>&1; then
    echo "    -> Using GNU parallel (${PARALLEL_JOBS} jobs)"
    {
      echo "$DOMAIN"
      cat "$SUBS_ALL"
    } | sort -u | parallel -j "${PARALLEL_JOBS}" --bar "echo https://{} | waybackurls 2>/dev/null || true" | sort -u > "$WAYBACK"
  else
    echo "    -> Using xargs for parallel processing"
    {
      echo "$DOMAIN"
      cat "$SUBS_ALL"
    } | sort -u | xargs -P "${PARALLEL_JOBS}" -I {} sh -c 'echo https://{} | waybackurls 2>/dev/null || true' | sort -u > "$WAYBACK"
  fi
  cp "$WAYBACK" "$URLS_ALL"
else
  echo "https://${DOMAIN}" | waybackurls 2>/dev/null | sort -u > "$WAYBACK" || touch "$WAYBACK"
  cp "$WAYBACK" "$URLS_ALL"
fi
step_done

# ---------- Step: GAU (if available) ----------
if command -v gau >/dev/null 2>&1; then
  echo "${bold}${cyan}[${step_num}/${total_steps}] Additional archived URLs (gau)${reset}"
  step_start_ts=$(date +%s)
  GAU_URLS="$OUTDIR/urls_gau.txt"
  echo "$DOMAIN" | gau --threads 5 --blacklist png,jpg,jpeg,gif,svg,css,woff,woff2,ttf,eot 2>/dev/null | sort -u > "$GAU_URLS" || touch "$GAU_URLS"
  cat "$GAU_URLS" >> "$URLS_ALL"
  sort -u "$URLS_ALL" -o "$URLS_ALL"
  step_done
fi

# ---------- Step: Pattern Filtering ----------
echo "${bold}${cyan}[${step_num}/${total_steps}] Pattern filtering (gf)${reset}"
step_start_ts=$(date +%s)
mkdir -p "$OUTDIR/patterns"

if command -v gf >/dev/null 2>&1 && [[ -s "$URLS_ALL" ]]; then
  gf xss < "$URLS_ALL" 2>/dev/null | sort -u > "$OUTDIR/patterns/xss.txt" || touch "$OUTDIR/patterns/xss.txt"
  gf sqli < "$URLS_ALL" 2>/dev/null | sort -u > "$OUTDIR/patterns/sqli.txt" || touch "$OUTDIR/patterns/sqli.txt"
  gf ssrf < "$URLS_ALL" 2>/dev/null | sort -u > "$OUTDIR/patterns/ssrf.txt" || touch "$OUTDIR/patterns/ssrf.txt"
  gf redirect < "$URLS_ALL" 2>/dev/null | sort -u > "$OUTDIR/patterns/redirect.txt" || touch "$OUTDIR/patterns/redirect.txt"
  gf lfi < "$URLS_ALL" 2>/dev/null | sort -u > "$OUTDIR/patterns/lfi.txt" || touch "$OUTDIR/patterns/lfi.txt"
  gf rce < "$URLS_ALL" 2>/dev/null | sort -u > "$OUTDIR/patterns/rce.txt" || touch "$OUTDIR/patterns/rce.txt"
else
  echo "    -> gf not available or no URLs, skipping"
fi

if [[ -s "$URLS_ALL" ]]; then
  grep -oE '\.(js|json|xml|yaml|yml|config|conf|bak|backup|old|sql|db|env|log)(\?|$)' "$URLS_ALL" 2>/dev/null | \
    cut -d'?' -f1 | sort -u > "$OUTDIR/patterns/interesting_extensions.txt" || touch "$OUTDIR/patterns/interesting_extensions.txt"
  grep -oE '\?[^[:space:]]+' "$URLS_ALL" 2>/dev/null | sort -u > "$OUTDIR/patterns/parameters.txt" || touch "$OUTDIR/patterns/parameters.txt"
fi
step_done

# ============================================================
# PHASE 2: ACTIVE RECONNAISSANCE (ACTIVE/FULL MODES ONLY)
# ============================================================

if [[ "$MODE" == "active" ]] || [[ "$MODE" == "full" ]]; then
  echo "${bold}${cyan}═══════════════════════════════════════════════${reset}"
  echo "${bold}${yellow}  PHASE 2: ACTIVE RECONNAISSANCE${reset}"
  echo "${bold}${cyan}═══════════════════════════════════════════════${reset}"
  echo
  
  # ---------- Step: HTTPx ----------
  echo "${bold}${cyan}[${step_num}/${total_steps}] Live host probing (httpx)${reset}"
  step_start_ts=$(date +%s)
  LIVE="$OUTDIR/live.txt"
  httpx -l "$SUBS_ALL" -silent -o "$LIVE" -threads 30 -timeout 10 -retries 1 -no-color 2>/dev/null || \
    cat "$SUBS_ALL" | httpx -silent -o "$LIVE" -threads 30 -timeout 10 -retries 1 -no-color 2>/dev/null || true
  step_done
  
  # ---------- Step: Nuclei ----------
  echo "${bold}${cyan}[${step_num}/${total_steps}] Vulnerability scanning (nuclei)${reset}"
  step_start_ts=$(date +%s)
  NUCLEI_OUT="$OUTDIR/nuclei-results.txt"
  if [[ -d ~/tools/nuclei-templates ]]; then
    nuclei -l "$LIVE" -t ~/tools/nuclei-templates -o "$NUCLEI_OUT" \
      -c "${THREADS}" -bulk-size 25 -timeout 10 -rl 150 -silent 2>/dev/null || true
  else
    nuclei -l "$LIVE" -o "$NUCLEI_OUT" \
      -c "${THREADS}" -bulk-size 25 -timeout 10 -rl 150 -silent 2>/dev/null || true
  fi
  step_done
  
  # ---------- Step: GF on live hosts ----------
  echo "${bold}${cyan}[${step_num}/${total_steps}] Pattern matching on live hosts${reset}"
  step_start_ts=$(date +%s)
  GF_XSS="$OUTDIR/gf_xss_live.txt"
  if command -v gf >/dev/null 2>&1 && [[ -s "$WAYBACK" ]]; then
    gf xss < "$WAYBACK" | sort -u > "$GF_XSS" || true
  else
    : > "$GF_XSS"
  fi
  step_done
fi

# ============================================================
# PHASE 3: DIRECTORY FUZZING (FULL MODE ONLY)
# ============================================================

if [[ "$MODE" == "full" ]] && [[ -n "$WORDLIST" ]]; then
  echo "${bold}${cyan}═══════════════════════════════════════════════${reset}"
  echo "${bold}${red}  PHASE 3: DIRECTORY FUZZING${reset}"
  echo "${bold}${cyan}═══════════════════════════════════════════════${reset}"
  echo
  
  echo "${bold}${cyan}[${step_num}/${total_steps}] Directory fuzzing (ffuf)${reset}"
  step_start_ts=$(date +%s)
  FFUF_OUT="$OUTDIR/ffuf.json"
  FIRST_HOST="$(head -n1 "$LIVE" 2>/dev/null || true)"
  
  if [[ -z "$FIRST_HOST" ]]; then
    echo "    -> No live hosts found, skipping ffuf"
  else
    PATHS="$OUTDIR/ffuf_paths.txt"
    if [[ -s "$WAYBACK" ]]; then
      sed -E 's#https?://[^/]+##; /^$/d' "$WAYBACK" | sort -u > "$PATHS"
    else
      cp "$WORDLIST" "$PATHS"
    fi
    ffuf -w "$PATHS" -u "${FIRST_HOST}/FUZZ" \
      -mc 200,201,202,203,301,302,307,401,403,405 \
      -t "${THREADS}" -o "$FFUF_OUT" -of json \
      -ac -timeout 10 -se 2>/dev/null || true
    rm -f "$PATHS"
  fi
  step_done
fi

# ============================================================
# FINAL SUMMARY
# ============================================================

RUN_END_TS=$(date +%s)
TOTAL_ELAPSED=$((RUN_END_TS - RUN_START_TS))

# Count results
SUBS_COUNT=$(wc -l < "$SUBS_ALL" 2>/dev/null || echo "0")
URLS_COUNT=$(wc -l < "$URLS_ALL" 2>/dev/null || echo "0")
XSS_COUNT=$(wc -l < "$OUTDIR/patterns/xss.txt" 2>/dev/null || echo "0")
SQLI_COUNT=$(wc -l < "$OUTDIR/patterns/sqli.txt" 2>/dev/null || echo "0")
SSRF_COUNT=$(wc -l < "$OUTDIR/patterns/ssrf.txt" 2>/dev/null || echo "0")

echo "${bold}${cyan}═══════════════════════════════════════════════${reset}"
echo "${bold}${green}  RECONNAISSANCE COMPLETE${reset}"
echo "${bold}${cyan}═══════════════════════════════════════════════${reset}"
echo
echo "${bold}Total Time:${reset} $(print_elapsed $TOTAL_ELAPSED)"
echo "${bold}Mode:${reset} ${MODE}"
echo
echo "${bold}${cyan}Results Summary:${reset}"
echo "  Subdomains found     : ${green}${SUBS_COUNT}${reset}"
echo "  Archived URLs found  : ${green}${URLS_COUNT}${reset}"

if [[ "$MODE" == "active" ]] || [[ "$MODE" == "full" ]]; then
  LIVE_COUNT=$(wc -l < "$LIVE" 2>/dev/null || echo "0")
  echo "  Live hosts           : ${green}${LIVE_COUNT}${reset}"
fi

echo
echo "${bold}Vulnerability Patterns:${reset}"
echo "  XSS candidates       : ${yellow}${XSS_COUNT}${reset}"
echo "  SQLi candidates      : ${yellow}${SQLI_COUNT}${reset}"
echo "  SSRF candidates      : ${yellow}${SSRF_COUNT}${reset}"
echo

echo "${bold}Output Directory:${reset}"
echo "  ${cyan}${OUTDIR}${reset}"
echo "  ${cyan}${LOG_FILE}${reset} (run log)"
echo
echo "${bold}Key Files:${reset}"
echo "  📂 subdomains_all.txt           - All discovered subdomains"
echo "  📂 urls_all.txt                 - All archived URLs"
echo "  📂 patterns/xss.txt             - XSS candidates"
echo "  📂 patterns/sqli.txt            - SQLi candidates"
echo "  📂 patterns/ssrf.txt            - SSRF candidates"
echo "  📂 patterns/parameters.txt      - URL parameters"

if [[ "$MODE" == "active" ]] || [[ "$MODE" == "full" ]]; then
  echo "  📂 live.txt                     - Live hosts"
  echo "  📂 nuclei-results.txt           - Vulnerability scan results"
fi

if [[ "$MODE" == "full" ]] && [[ -n "$WORDLIST" ]]; then
  echo "  📂 ffuf.json                    - Directory fuzzing results"
fi

echo
echo "${bold}${green}Next Steps:${reset}"
echo "  1. Review subdomains for interesting targets"
echo "  2. Check pattern files for quick wins"
echo "  3. Manually verify promising findings"

if [[ "$MODE" == "passive" ]]; then
  echo "  4. Run in 'active' mode on promising subdomains (if authorized)"
fi

echo
case "$MODE" in
  passive)
    echo "${bold}${green}✓ Zero requests sent to ${DOMAIN}${reset}"
    ;;
  active|full)
    echo "${bold}${yellow}⚠ Active scanning performed on ${DOMAIN}${reset}"
    ;;
esac
echo "${yellow}⚠ Reminder: Only scan authorized targets within bug bounty scope${reset}"
