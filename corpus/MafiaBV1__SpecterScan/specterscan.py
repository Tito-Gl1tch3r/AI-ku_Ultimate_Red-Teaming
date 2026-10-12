#!/usr/bin/env python3
r"""
advanced_scan.py

WSL-aware pentest-samler med:
- passive OSINT/subdomain pipeline (assetfinder, subfinder, amass)
- ikke-aggressive verktøy (nmap -p- , whatweb, nikto, curl)
- aktive verktøy og DirBuster-støtte (bruk med forsiktighet)
- valgfrie aggressive verktøy (masscan, hydra, sqlmap, wpscan) som krever ekstra bekreftelse

Kjør KUN mot mål du har SKRIFTLIG tillatelse til å teste.
"""
import subprocess
import shutil
import os
import sys
import datetime
import pathlib
import shlex
import re
# ======== SpecterScan Branding ========
PROJECT_NAME = "SpecterScan"
PROJECT_TAGLINE = "Safe, lab-first reconnaissance toolkit · Non-destructive by default"
PROJECT_WARNING = "⚠️ WARNING: Use only against targets you have explicit written permission to test."

ASCII_BANNER = r"""
   ____                  _              _____                                 
  / ___| _ __   ___  ___| |_ ___ _ __  / ____|_  ____  _____  ___  _ __  ___  
  \___ \| '_ \ / _ \/ __| __/ _ \ '__|| (___\ \/ / _ \/ _ \ \/ / | '_ \/ _ \ 
   ___) | |_) |  __/ (__| ||  __/ |    \___ \>  <  __/  __/>  <| | | |  __/ 
  |____/| .__/ \___|\___|\__\___|_|    ____) /_/\_\___|\___/_/\_\_| |_|\___| 
        |_|                           |_____/                                

                           S P E C T E R S C A N
            Safe, lab-first reconnaissance · Non-destructive by default
"""

def print_banner(quiet: bool = False):
    """
    Print the ASCII banner unless quiet=True.
    """
    if quiet:
        return
    print(ASCII_BANNER)
    print(PROJECT_WARNING)
    print()  # spacer
# ======== End SpecterScan Branding ========
# --- auto wordlist helpers ---
import glob, urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORDLIST_DIRS = [
    os.path.join(BASE_DIR, "wordlists"),
    os.path.join(BASE_DIR, "scripts", "wordlists"),  # fallback for older structure
]

CURATED_WORDLISTS = {
    "subdomains-top1k.txt": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1k.txt",
    "usernames-top1k.txt":  "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Usernames/top-usernames-shortlist.txt",
    "passwords-10k.txt":    "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10k-most-common.txt",
}

def _first_wordlist_dir():
    for d in WORDLIST_DIRS:
        if os.path.isdir(d):
            return d
    d = os.path.join(BASE_DIR, "wordlists")
    os.makedirs(d, exist_ok=True)
    return d

def list_local_wordlists():
    wl_dir = _first_wordlist_dir()
    files = sorted([
        os.path.join(wl_dir, os.path.basename(p))
        for p in glob.glob(os.path.join(wl_dir, "*"))
        if os.path.isfile(p)
    ])
    return files

def ensure_curated_wordlists():
    """Download curated lists if wordlists dir is empty."""
    wl_dir = _first_wordlist_dir()
    have = [f for f in list_local_wordlists()]
    if have:
        return
    print("[i] No local wordlists found — downloading curated SecLists snippets...")
    for name, url in CURATED_WORDLISTS.items():
        dest = os.path.join(wl_dir, name)
        try:
            urllib.request.urlretrieve(url, dest)
            print(f"[+] downloaded {name}")
        except Exception as e:
            print(f"[!] failed to download {name}: {e}")

def auto_pick_wordlist(prefer=None):
    """Return a path to the 'best' available wordlist (optionally by substring)."""
    files = list_local_wordlists()
    if not files:
        return None
    if prefer:
        for f in files:
            if prefer.lower() in os.path.basename(f).lower():
                return f
    return files[0]


# ---------------- Konfig ----------------
NON_AGGRESSIVE_TOOLS = {
    "nmap": {
        # -p- = scan alle TCP-porter
        "cmd": lambda ip, url: ["nmap", "-p-", "-sV", "-sC", "-Pn", ip],
        "timeout": 3600,
        "desc": "Service/version + default scripts (ikke-aggressiv)"
    },
    "whatweb": {
        "cmd": lambda ip, url: ["whatweb", "--no-errors", url],
        "timeout": 60,
        "desc": "Web fingerprinting (passiv)"
    },
    "nikto": {
        "cmd": lambda ip, url: ["nikto", "-host", url],
        "timeout": 300,
        "desc": "Web vuln scanner (kan være støyende)"
    },
    "curl_headers": {
        "cmd": lambda ip, url: ["curl", "-I", "--insecure", url],
        "timeout": 20,
        "desc": "Henter HTTP-headere"
    }
}

# Verktøy for subdomain/osint pipeline (passive først)
SUBDOMAIN_TOOLS_PASSIVE = [
    ("assetfinder", ["assetfinder", "--subs-only"]),
    ("subfinder", ["subfinder", "-silent", "-d"]),
    ("amass", ["amass", "enum", "-passive", "-d"])  # -passive for å unngå støy
]

# Aktive/valgfri verktøy (kjør kun hvis bruker godkjenner)
OPTIONAL_ACTIVE_TOOLS = [
    ("massdns", ["massdns"]),
    ("altdns", ["altdns"]),
    ("gobuster", ["gobuster", "dir", "-u"]),
    ("ffuf", ["ffuf", "-u"]),
    ("aquatone", ["aquatone"]),
    ("dirbuster", ["dirbuster"])  # GUI/tool that may have CLI depending on installation
]

# Aggressive verktøy (krever ekstra bekreftelse)
AGGRESSIVE_TOOLS = [
    ("masscan", ["masscan"]),   # Very fast port scanner — can be disruptive
    ("hydra", ["hydra"]),       # Password brute-force tool
    ("sqlmap", ["sqlmap"]),     # Automatic SQL injection finder/exploiter
    ("wpscan", ["wpscan"])      # WordPress vulnerability scanner (can be noisy)
]

# ---------------- Hjelpefunksjoner ----------------
def is_wsl():
    try:
        if "WSL_DISTRO_NAME" in os.environ:
            return True
        with open("/proc/version", "r", encoding="utf-8") as f:
            txt = f.read()
            if "microsoft" in txt.lower():
                return True
    except Exception:
        pass
    return False

def winpath_to_wsl(win_path):
    r"""Konverter en Windows-sti (C:\...) til WSL-sti ved å bruke wslpath hvis tilgjengelig."""
    wslpath_bin = shutil.which("wslpath")
    if not wslpath_bin:
        return win_path
    try:
        cp = subprocess.run([wslpath_bin, "-a", win_path], capture_output=True, text=True, timeout=5)
        if cp.returncode == 0:
            return cp.stdout.strip()
    except Exception:
        pass
    return win_path

def looks_like_windows_path(p):
    return bool(re.match(r"^[A-Za-z]:[\\/]", p))

def check_tool_exists(bin_name):
    return shutil.which(bin_name) is not None

def safe_mkdir(path):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)

def timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def run_command(cmd_list, timeout):
    """
    Kjører kommando, returnerer (returncode, stdout, stderr, timed_out_bool)
    """
    try:
        proc = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired as e:
        out = e.stdout or ""
        err = e.stderr or ""
        timeout_msg = "\n[ERROR] TIMEOUT after {} seconds".format(timeout)
        return -1, out, err + timeout_msg, True
    except Exception as e:
        return -1, "", str(e), False

def sanitize_filename(s):
    return "".join(c for c in s if c.isalnum() or c in ("-", "_", ".")).rstrip(".")

# ---------------- Subdomain / OSINT pipeline ----------------
def run_subdomain_pipeline(target_domain, outdir, timeout_each=120):
    """Kjør passive subdomain-verktøy (assetfinder, subfinder, amass) om de finnes.
    Returnerer sti til fil med samlet subdomain-liste (eller None hvis ingen funnet).
    """
    collected = set()

    for name, base_cmd in SUBDOMAIN_TOOLS_PASSIVE:
        bin_name = base_cmd[0]
        if not check_tool_exists(bin_name):
            print(f"[WARN] {bin_name} ikke funnet — hopper over {name}.")
            continue

        # Bygg kommando
        if name == "subfinder":
            cmd = ["subfinder", "-d", target_domain, "-silent"]
        elif name == "assetfinder":
            cmd = ["assetfinder", "--subs-only", target_domain]
        elif name == "amass":
            cmd = ["amass", "enum", "-passive", "-d", target_domain]
        else:
            cmd = base_cmd + [target_domain]

        print(f"[RUN] {shlex.join(cmd)}")
        rc, out, err, timed_out = run_command(cmd, timeout_each)
        if out:
            for line in out.splitlines():
                line = line.strip()
                if not line:
                    continue
                # rens opp prefiks/suffiks
                line = re.sub(r"^https?://", "", line)
                line = line.split("/")[0]
                if target_domain in line:
                    collected.add(line.lower())
        if err:
            print(f"[{name}] STDERR (kort): {err.splitlines()[:3]}")

    if not collected:
        print("[INFO] Fant ingen subdomener med passive verktøyene som var tilgjengelige.")
        return None

    sub_file = os.path.join(outdir, f"{sanitize_filename(target_domain)}_subdomains.txt")
    try:
        with open(sub_file, "w", encoding="utf-8") as f:
            for s in sorted(collected):
                f.write(s + "\n")
        print(f"[SAVED] Kombinert subdomain-liste -> {sub_file}")
    except Exception as e:
        print(f"[FEIL] Kunne ikke skrive subdomain-fil: {e}")
        return None

    # Enkel resolve med host/dig hvis tilgjengelig
    resolver_bin = shutil.which("host") or shutil.which("dig")
    if resolver_bin:
        resolved_file = os.path.join(outdir, f"{sanitize_filename(target_domain)}_resolved.txt")
        resolved = {}
        for s in sorted(collected):
            if resolver_bin.endswith("host"):
                cmd = ["host", s]
            else:
                cmd = ["dig", "+short", s]
            rc, out, err, _ = run_command(cmd, 15)
            addrs = [ln.strip() for ln in (out or "").splitlines() if ln.strip()]
            if addrs:
                resolved[s] = addrs
        try:
            with open(resolved_file, "w", encoding="utf-8") as f:
                for s, addrs in resolved.items():
                    f.write(f"{s} -> {', '.join(addrs)}\n")
            print(f"[SAVED] Resolved subdomains -> {resolved_file}")
        except Exception as e:
            print(f"[FEIL] Kunne ikke skrive resolved-fil: {e}")

    return sub_file

def run_dirbuster(target_url, outdir, wordlist=None, threads=50, timeout=3600, jar_path=None):
    """
    Kjør DirBuster i en ikke-interaktiv modus om mulig.

    Strategi:
    - Hvis `dirbuster`-bin finnes, prøv å kjøre: dirbuster -u <url> -l <wordlist> -t <threads> -o <outfile>
    - Ellers, hvis en DirBuster JAR er oppgitt via `jar_path`, kjør: java -jar <jar> -u <url> -l <wordlist> -t <threads> -o <outfile>
    - Ellers fall tilbake til `dirb` hvis tilgjengelig: dirb <url> <wordlist> -o <outfile>

    Merk: DirBuster-distribusjoner varierer — sjekk `--help` for din versjon. Wordlist må oppgis for brute-force.
    """
    if not wordlist:
        picked = auto_pick_wordlist(prefer="subdomain") or auto_pick_wordlist(prefer="dir") or auto_pick_wordlist()
        if picked:
            print(f"[i] No wordlist provided; auto-selected: {picked}")
            wordlist = picked
        else:
            print("[WARN] DirBuster requires a wordlist and none were found locally.")
            ensure_curated_wordlists()
            picked = auto_pick_wordlist()
            if picked:
                print(f"[i] Auto-selected after download: {picked}")
                wordlist = picked
            else:
                return None

    safe_name = sanitize_filename(target_url.replace("https://", "").replace("http://", "").rstrip('/'))
    out_file = os.path.join(outdir, f"dirbuster_{safe_name}.txt")

    # Prioriter native bin
    if check_tool_exists("dirbuster"):
        cmd = ["dirbuster", "-u", target_url, "-l", wordlist, "-t", str(threads), "-o", out_file]
    elif jar_path and os.path.isfile(jar_path):
        cmd = ["java", "-jar", jar_path, "-u", target_url, "-l", wordlist, "-t", str(threads), "-o", out_file]
    elif check_tool_exists("dirb"):
        # dirb er enklere CLI-alternativ
        cmd = ["dirb", target_url, wordlist, "-o", out_file]
    else:
        print("[WARN] Ingen DirBuster/dirb/java funnet — kan ikke kjøre DirBuster automatisk.")
        return None

    print(f"[RUN] {shlex.join(cmd)} (timeout {timeout}s)")
    rc, out, err, timed_out = run_command(cmd, timeout)

    try:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(f"Command: {shlex.join(cmd)}\nReturncode: {rc}\nTimed out: {timed_out}\n\n--- STDOUT ---\n")
            f.write(out or "")
            f.write("\n\n--- STDERR ---\n")
            f.write(err or "")
        print(f"[SAVED] {out_file}")
    except Exception as e:
        print(f"[FEIL] Kunne ikke skrive {out_file}: {e}")

    return out_file

# ---------------- Aggressive tools helpers ----------------
def require_aggressive_confirmation():
    """
    Krever ekstra uttrykkelig bekreftelse før kjøring av aggressive verktøy.
    Brukeren må skrive nøyaktig: I HAVE PERMISSION
    """
    print("\n=== ADVARSEL: AGGRESSIVE VERKTØY ===")
    print("Du har bedt om å kjøre aggressive verktøy (masscan, hydra, sqlmap, wpscan). Dette kan være svært støyende og potensielt skadelig.")
    print("Du må skrive følgende eksakt for å bekrefte at du har skriftlig tillatelse: I HAVE PERMISSION")
    v = input("Skriv nå: ").strip()
    return v == "I HAVE PERMISSION"

def run_masscan(target_ip, outdir):
    rate = input("Oppgi masscan rate (pakker/sec), anbefalt 1000 eller lavere: ").strip() or "1000"
    out_file = os.path.join(outdir, f"masscan_{sanitize_filename(target_ip)}.txt")
    cmd = ["masscan", "-p1-65535", target_ip, "--rate", rate]
    print(f"[RUN] {shlex.join(cmd)}")
    rc, out, err, timed_out = run_command(cmd, 3600)
    try:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(f"Command: {shlex.join(cmd)}\nReturncode: {rc}\nTimed out: {timed_out}\n\n--- STDOUT ---\n")
            f.write(out or "")
            f.write("\n\n--- STDERR ---\n")
            f.write(err or "")
        print(f"[SAVED] {out_file}")
    except Exception as e:
        print(f"[FEIL] Kunne ikke skrive {out_file}: {e}")
    return out_file

def run_hydra(target_ip):
    print("Hydra krever at du oppgir tjeneste (f.eks. ssh, ftp, http-post-form) og wordlist-filer.")
    service = input("Tjeneste (f.eks. ssh): ").strip()
    userlist = input("Path til brukernavnsliste (-L) (Enter to auto-select or skip): ").strip()
    passlist = input("Path til passordliste (-P) (Enter to auto-select): ").strip()

    # auto-pick passlist if blank
    if not passlist:
        passlist_path = auto_pick_wordlist(prefer="pass") or auto_pick_wordlist(prefer="password") or auto_pick_wordlist()
        if passlist_path:
            passlist = passlist_path
            print(f"[i] Auto-selected password list: {os.path.basename(passlist)}")
        else:
            print("Hopper over hydra — ingen passordliste tilgjengelig.")
            return None

    # auto-pick userlist if blank
    if not userlist:
        userlist_path = auto_pick_wordlist(prefer="user") or auto_pick_wordlist(prefer="username")
        if userlist_path:
            userlist = userlist_path
            print(f"[i] Auto-selected user list: {os.path.basename(userlist)}")
        else:
            single_user = input("Oppgi enkeltbrukernavn (-l) hvis du ønsker (tryk Enter for ikke): ").strip()
            if not single_user:
                print("[i] No userlist provided and no local userlist found; aborting hydra.")
                return None
    target = input(f"Mål (IP eller hostname) [{target_ip}]: ").strip() or target_ip
    out_file = f"hydra_{sanitize_filename(target)}_{service}.txt"
    cmd = ["hydra"]
    if userlist:
        cmd += ["-L", userlist]
    else:
        single_user = input("Oppgi enkeltbrukernavn (-l) hvis du ønsker (tryk Enter for ikke): ").strip()
        if single_user:
            cmd += ["-l", single_user]
    cmd += ["-P", passlist, f"{service}://{target}"]
    print(f"[RUN] {shlex.join(cmd)}")
    rc, out, err, timed_out = run_command(cmd, 7200)
    try:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(f"Command: {shlex.join(cmd)}\nReturncode: {rc}\nTimed out: {timed_out}\n\n--- STDOUT ---\n")
            f.write(out or "")
            f.write("\n\n--- STDERR ---\n")
            f.write(err or "")
        print(f"[SAVED] {out_file}")
    except Exception as e:
        print(f"[FEIL] Kunne ikke skrive {out_file}: {e}")
    return out_file

def run_sqlmap(target_url, outdir):
    print("SQLMap vil kjøre mot en URL. Oppgi full URL inkl. parameter (f.eks. 'http://target/page.php?id=1')")
    url = input("Mål-URL: ").strip() or target_url
    out_file = os.path.join(outdir, f"sqlmap_{sanitize_filename(url)}.txt")
    # Standard sikker modus: --batch for non-interactive, --risk=1 --level=1
    cmd = ["sqlmap", "-u", url, "--batch", "--risk=1", "--level=1"]
    print(f"[RUN] {shlex.join(cmd)} (kan ta lang tid)")
    rc, out, err, timed_out = run_command(cmd, 7200)
    try:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(f"Command: {shlex.join(cmd)}\nReturncode: {rc}\nTimed out: {timed_out}\n\n--- STDOUT ---\n")
            f.write(out or "")
            f.write("\n\n--- STDERR ---\n")
            f.write(err or "")
        print(f"[SAVED] {out_file}")
    except Exception as e:
        print(f"[FEIL] Kunne ikke skrive {out_file}: {e}")
    return out_file

def run_wpscan(target_url, outdir):
    print("WPScan: oppgi URL til WordPress-site (inkl. http(s)://)")
    url = input("WP mål-URL: ").strip() or target_url
    out_file = os.path.join(outdir, f"wpscan_{sanitize_filename(url)}.txt")
    # Kjør med --enumerate vp, --batch
    cmd = ["wpscan", "--url", url, "--enumerate", "vp,vt,u", "--no-banner"]
    print(f"[RUN] {shlex.join(cmd)}")
    rc, out, err, timed_out = run_command(cmd, 3600)
    try:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(f"Command: {shlex.join(cmd)}\nReturncode: {rc}\nTimed out: {timed_out}\n\n--- STDOUT ---\n")
            f.write(out or "")
            f.write("\n\n--- STDERR ---\n")
            f.write(err or "")
        print(f"[SAVED] {out_file}")
    except Exception as e:
        print(f"[FEIL] Kunne ikke skrive {out_file}: {e}")
    return out_file

# ---------------- Hovedprogram ----------------
def main():
    print_banner(quiet=False)

    target_ip = input("Skriv target IP (f.eks. 192.168.34.194): ").strip()
    target_url = input("Skriv target domene/URL (f.eks. http://192.168.34.194 eller example.com): ").strip()
    outdir_input = input("Valgfritt: ønsket output-mappe (tryk Enter for standard 'outputs/'): ").strip()

    if not target_ip or not target_url:
        print("IP eller URL ikke oppgitt — avslutter.")
        sys.exit(1)

    running_in_wsl = is_wsl()
    if running_in_wsl:
        print("[INFO] Kjøres under WSL.")
    else:
        print("[INFO] Kjøres på vanlig Linux.")

    # Behandle outdir
    if outdir_input:
        chosen_outdir = outdir_input
        if running_in_wsl and looks_like_windows_path(chosen_outdir):
            conv = winpath_to_wsl(chosen_outdir)
            if conv != chosen_outdir:
                print(f"[INFO] Konverterte Windows-path -> WSL-path: '{chosen_outdir}' -> '{conv}'")
                chosen_outdir = conv
            else:
                print("[WARN] Kunne ikke konvertere Windows-path (wslpath ikke tilgjengelig).")
    else:
        safe_name = sanitize_filename(target_ip + "_" + timestamp())
        chosen_outdir = os.path.join("outputs", safe_name)

    safe_mkdir(chosen_outdir)
    combined_path = os.path.join(chosen_outdir, f"{sanitize_filename(target_ip)}_combined.txt")
    print(f"[INFO] Resultater lagres i: {chosen_outdir}")

    # Kjør subdomain pipeline først (passive)
    run_passive = input("Kjør passive subdomain/OSINT-verktøy først? [Y/n]: ").strip().lower() or "y"
    subdomains_file = None
    if run_passive.startswith("y"):
        # Hent domain for pipeline (fjern http:// hvis gitt)
        domain_for_pipeline = re.sub(r"^https?://", "", target_url).split("/")[0]
        subdomains_file = run_subdomain_pipeline(domain_for_pipeline, chosen_outdir)

    # Sjekk og kjør ikke-aggressive verktøy
    available = {}
    for key, cfg in NON_AGGRESSIVE_TOOLS.items():
        bin_name = cfg["cmd"](target_ip, target_url)[0]
        if check_tool_exists(bin_name):
            available[key] = cfg
            print(f"[OK] {bin_name} funnet.")
        else:
            print(f"[ADVARSEL] {bin_name} ikke funnet — hopper over {key}.")

    if not available:
        print("Ingen ikke-aggressive verktøy funnet. Avslutter.")
        sys.exit(1)

    # Spør om bruker vil kjøre aktive tools hvis noen er installert
    active_present = any(check_tool_exists(t[0]) for t in OPTIONAL_ACTIVE_TOOLS)
    run_active = False
    if active_present:
        ans = input("Noen aktive verktøy er tilgjengelige (gobuster/ffuf/massdns/dirbuster...). Vil du kjøre dem? [n] ").strip().lower() or "n"
        run_active = ans.startswith("y")

    # Kjør hvert ikke-aggressive verktøy og logg
    with open(combined_path, "w", encoding="utf-8") as combined_f:
        combined_f.write(f"Scan report for {target_ip} / {target_url}\nGenerated: {datetime.datetime.now().isoformat()}\n\n")
        for name, cfg in available.items():
            cmd = cfg["cmd"](target_ip, target_url)
            timeout = cfg.get("timeout", 120)
            human = f"{name}_{sanitize_filename(target_ip)}"
            out_file = os.path.join(chosen_outdir, human + ".txt")

            header = f"\n\n=== Tool: {shlex.join(cmd)} ===\nStart: {datetime.datetime.now().isoformat()}\nTimeout: {timeout}s\n\n"
            print(f"\n[RUN] {shlex.join(cmd)} (timeout {timeout}s)")
            combined_f.write(header)

            rc, out, err, timed_out = run_command(cmd, timeout)

            try:
                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(f"Command: {shlex.join(cmd)}\nReturncode: {rc}\nTimed out: {timed_out}\n\n--- STDOUT ---\n")
                    f.write(out or "")
                    f.write("\n\n--- STDERR ---\n")
                    f.write(err or "")
                print(f"[SAVED] {out_file}")
            except Exception as e:
                print(f"[FEIL] Kunne ikke skrive {out_file}: {e}")

            combined_f.write(f"--- {name} STDOUT ---\n")
            combined_f.write((out or "") + "\n")
            combined_f.write(f"--- {name} STDERR ---\n")
            combined_f.write((err or "") + "\n")
            combined_f.write(f"--- end {name} (returncode={rc}, timed_out={timed_out}) ---\n")

    # Hvis bruker vil kjøre aktive verktøy, kjør en enkel, ansvarlig sekvens
    if run_active:
        print("[INFO] Kjører aktive verktøy — dette kan generere støy. Bekreftet av bruker.")
        for bin_name, base_cmd in OPTIONAL_ACTIVE_TOOLS:
            if not check_tool_exists(bin_name):
                continue
            ok = input(f"Vil du kjøre {bin_name} (kort, ansvarlig modus)? [n] ").strip().lower() or "n"
            if not ok.startswith("y"):
                continue

            if bin_name == "gobuster":
                wordlist = input("Path til wordlist for gobuster (press Enter to auto-select): ").strip()
                if not wordlist:
                    wordlist = auto_pick_wordlist(prefer="subdomain") or auto_pick_wordlist(prefer="dir") or auto_pick_wordlist()
                    if wordlist:
                        print(f"[i] Auto-selected: {os.path.basename(wordlist)}")
                    else:
                        print("Hopper over gobuster — ingen wordlist tilgjengelig.")
                        continue
                cmd = ["gobuster", "dir", "-u", target_url if target_url.startswith("http") else f"http://{target_url}", "-w", wordlist, "-t", "20"]
                timeout = 600
            elif bin_name == "ffuf":
                wordlist = input("Path til wordlist for ffuf (press Enter to auto-select): ").strip()
                if not wordlist:
                    wordlist = auto_pick_wordlist(prefer="subdomain") or auto_pick_wordlist(prefer="dir") or auto_pick_wordlist()
                    if wordlist:
                        print(f"[i] Auto-selected: {os.path.basename(wordlist)}")
                    else:
                        print("Hopper over ffuf — ingen wordlist tilgjengelig.")
                        continue
                cmd = ["ffuf", "-u", f"{target_url.rstrip('/')}/FUZZ", "-w", wordlist, "-t", "40"]
                timeout = 600
            elif bin_name == "massdns":
                print("massdns krever ofte en resolver-liste og inputfil. Sørg for å bruke den korrekt.")
                cmd = ["massdns", "--help"]
                timeout = 30
            elif bin_name == "dirbuster":
                wordlist = input("Path til wordlist for DirBuster (f.eks. /usr/share/wordlists/common.txt): ").strip()
                jar = input("Valgfritt: path til DirBuster JAR (tryk Enter for ikke): ").strip() or None
                if not wordlist:
                    print("Hopper over DirBuster — ingen wordlist oppgitt.")
                    continue
                out = run_dirbuster(target_url if target_url.startswith("http") else f"http://{target_url}", chosen_outdir, wordlist=wordlist, threads=50, timeout=3600, jar_path=jar)
                continue
            else:
                cmd = base_cmd + [target_url]
                timeout = 300

            human = f"active_{bin_name}_{sanitize_filename(target_ip)}"
            out_file = os.path.join(chosen_outdir, human + ".txt")
            print(f"[RUN] {shlex.join(cmd)} (timeout {timeout}s)")
            rc, out, err, timed_out = run_command(cmd, timeout)
            try:
                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(f"Command: {shlex.join(cmd)}\nReturncode: {rc}\nTimed out: {timed_out}\n\n--- STDOUT ---\n")
                    f.write(out or "")
                    f.write("\n\n--- STDERR ---\n")
                    f.write(err or "")
                print(f"[SAVED] {out_file}")
            except Exception as e:
                print(f"[FEIL] Kunne ikke skrive {out_file}: {e}")

    # ---------- Aggressive tools (ekstra bekreftelse kreves) ----------
    agg_present = any(check_tool_exists(t[0]) for t in AGGRESSIVE_TOOLS)
    if agg_present:
        run_agg = input("Aggressive verktøy er installert (masscan/hydra/sqlmap/wpscan). Vil du kjøre dem? [n] ").strip().lower() or "n"
        if run_agg.startswith("y"):
            if not require_aggressive_confirmation():
                print("Bekreftelse feilet — hopper over aggressive verktøy.")
            else:
                print("Bekreftet. Kjører aggressive verktøy etter brukerens valg.")
                # ensure wordlists exist (download curated if folder empty)
                ensure_curated_wordlists()
                if check_tool_exists("masscan"):
                    run_masscan(target_ip, chosen_outdir)
                if check_tool_exists("hydra"):
                    run_hydra(target_ip)
                if check_tool_exists("sqlmap"):
                    run_sqlmap(target_url, chosen_outdir)
                if check_tool_exists("wpscan"):
                    run_wpscan(target_url, chosen_outdir)

    print("\nFerdig! Se output i:", chosen_outdir)
    if running_in_wsl and outdir_input and looks_like_windows_path(outdir_input):
        print(r"Merk: Dersom du forventet å finne filene på Windows-siden, åpne den konverterte WSL-stien i Filutforsker (f.eks. \\wsl$\\).")

if __name__ == "__main__":
    main()
