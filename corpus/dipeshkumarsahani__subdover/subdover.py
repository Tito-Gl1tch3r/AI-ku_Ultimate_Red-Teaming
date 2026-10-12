# Subdover - Professional Subdomain Takeover Scanner
# Author: Dipesh Kumar Sahani
# GitHub: https://github.com/dipeshkumarsahani

import argparse
import requests
import dns.resolver
import os
import json
import time
from datetime import datetime
from colorama import Fore, Style, init
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from bs4 import BeautifulSoup

init(autoreset=True)
TOOL_VERSION = "1.0"
AUTHOR = "Dipesh Kumar Sahani"

# ---------------------- Banner ------------------------
def banner():
    print(Fore.MAGENTA + r"""
          _         _                     
 ___ _   _| |__   __| | _____   _____ _ __ 
/ __| | | | '_ \ / _` |/ _ \ \ / / _ \ '__|
\__ \ |_| | |_) | (_| | (_) \ V /  __/ |   
|___/\__,_|_.__/ \__,_|\___/ \_/ \___|_| 

        Subdover - Subdomain Takeover Scanner
         by Dipesh Kumar Sahani
   GitHub: https://github.com/dipeshkumarsahani
""")
    print(Fore.YELLOW + f"Version: {TOOL_VERSION} | Author: {AUTHOR}\n")

# ---------------------- Fingerprints -------------------
def generate_fingerprints():
    print("[DEBUG] Generating default fingerprints if not present.")
    default_fp = {
        "github.io": {"service": "GitHub Pages", "fingerprint": "There isn't a GitHub Pages site here."},
        "herokudns.com": {"service": "Heroku", "fingerprint": "No such app"},
        "bitbucket.io": {"service": "Bitbucket Pages", "fingerprint": "Repository not found"},
        "cloudfront.net": {"service": "CloudFront", "fingerprint": "ERROR: The request could not be satisfied"},
        "netlify.app": {"service": "Netlify", "fingerprint": "Page Not Found"},
        "readthedocs.io": {"service": "ReadTheDocs", "fingerprint": "unknown domain"},
        "surge.sh": {"service": "Surge", "fingerprint": "project not found"}
    }
    if not os.path.exists("fingerprints.json"):
        with open("fingerprints.json", "w") as f:
            json.dump(default_fp, f, indent=2)
        print("[INFO] fingerprints.json created.")

# ---------------------- DNS & HTTP -------------------
def get_cname(subdomain):
    print(f"[DEBUG] Resolving CNAME for {subdomain}")
    try:
        answers = dns.resolver.resolve(subdomain, 'CNAME')
        for rdata in answers:
            cname = str(rdata.target).strip('.')
            print(f"[INFO] CNAME for {subdomain} is {cname}")
            return cname
    except Exception as e:
        print(f"[ERROR] Failed to resolve CNAME for {subdomain}: {e}")
        return None

def get_http_response(subdomain, https=False):
    url = f"{'https' if https else 'http'}://{subdomain}"
    print(f"[DEBUG] Sending HTTP request to {url}")
    try:
        r = requests.get(url, timeout=6)
        print(f"[INFO] Received response from {url} with status {r.status_code}")
        return r.status_code, r.text
    except Exception as e:
        print(f"[ERROR] Request to {url} failed: {e}")
        return None, ""

# ---------------------- Fingerprint Match -------------------
def load_fingerprints():
    print("[DEBUG] Loading fingerprints from file.")
    generate_fingerprints()
    with open("fingerprints.json") as f:
        return json.load(f)

def extract_title(html):
    try:
        soup = BeautifulSoup(html, 'html.parser')
        return soup.title.string.strip() if soup.title else ""
    except:
        return ""

def check_fingerprint(cname, body, fingerprints):
    print(f"[DEBUG] Checking fingerprints for CNAME: {cname}")
    title = extract_title(body)
    for domain, data in fingerprints.items():
        if domain in cname and (data['fingerprint'] in body or data['fingerprint'] in title):
            print(f"[MATCH] Found matching fingerprint for {cname} ({data['service']})")
            return True, data['service']
    return False, None

# ---------------------- Scanner Core -------------------
def is_wildcard_dns(domain):
    print(f"[DEBUG] Checking for wildcard DNS on domain: {domain}")
    fake = f"nonexist-{int(time.time())}.{domain}"
    return get_cname(fake) is not None

def scan_subdomain(sub, use_https, fingerprints):
    print(f"[SCAN] Scanning subdomain: {sub}")
    result = {"subdomain": sub, "status": "Not Vulnerable", "cname": None, "platform": None}
    cname = get_cname(sub)
    if cname:
        result['cname'] = cname
        status, body = get_http_response(sub, use_https)
        if body:
            vuln, platform = check_fingerprint(cname, body, fingerprints)
            if vuln:
                result.update({"status": "VULNERABLE", "platform": platform})
    else:
        result['status'] = "NO CNAME"
    return result

# ---------------------- Results -------------------
def save_results(results, output, fmt):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(output, f"subdover_results_{ts}.{fmt}")
    with open(path, 'w') as f:
        if fmt == 'csv':
            f.write("Subdomain,CNAME,Platform,Status\n")
            for r in results:
                f.write(f"{r['subdomain']},{r.get('cname','')},{r.get('platform','')},{r['status']}\n")
        elif fmt == 'json':
            json.dump(results, f, indent=2)
        else:
            for r in results:
                f.write(f"{r['status']} - {r['subdomain']} => {r.get('cname','')} ({r.get('platform','')})\n")
    print(Fore.CYAN + f"\n✅ Results saved to {path}")

# ---------------------- Main -------------------
def main():
    banner()
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--subdomain", help="Scan a single subdomain")
    group.add_argument("-l", "--list", help="File containing subdomains")
    parser.add_argument("-o", "--output", default=".", help="Directory to save output")
    parser.add_argument("--format", default="csv", choices=['csv', 'json', 'txt'], help="Output format")
    parser.add_argument("--https", action='store_true', help="Use HTTPS for requests")
    parser.add_argument("--threads", type=int, default=10, help="Number of threads")
    parser.add_argument("--version", action='store_true', help="Show version and exit")
    args = parser.parse_args()

    if args.version:
        print(f"Subdover v{TOOL_VERSION} by {AUTHOR}")
        return

    if args.list and not os.path.exists(args.list):
        print(Fore.RED + f"[!] File not found: {args.list}")
        return

    subs = list(set([args.subdomain] if args.subdomain else open(args.list).read().splitlines()))
    subs = [s.strip() for s in subs if s.strip() and not s.startswith('#')]
    print(f"[INFO] Loaded {len(subs)} subdomains to scan.")
    domain = subs[0].split('.', 1)[-1]
    if is_wildcard_dns(domain):
        print(Fore.YELLOW + f"[!] Wildcard DNS detected for: {domain} — may cause false positives\n")

    fingerprints = load_fingerprints()
    results = []
    start = time.time()
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {executor.submit(scan_subdomain, sub, args.https, fingerprints): sub for sub in subs}
        for future in as_completed(futures):
            res = future.result()
            color = Fore.GREEN if res['status'] == "VULNERABLE" else (Fore.RED if res['status'] == "NO CNAME" else Fore.WHITE)
            print(color + f"{res['status']}: {res['subdomain']} => {res.get('cname','')} ({res.get('platform','')})")
            results.append(res)

    elapsed = round(time.time() - start, 2)
    print(Fore.BLUE + f"\n📊 Scan complete in {elapsed}s | Total: {len(results)} | Vulnerable: {sum(1 for r in results if r['status'] == 'VULNERABLE')}")
    save_results(results, args.output, args.format)

if __name__ == "__main__":
    main()
