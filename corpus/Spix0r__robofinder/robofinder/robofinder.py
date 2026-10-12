from requests.sessions import Session
from threading import local, Lock
import signal, sys, validators, re, datetime, argparse, time, requests, random
from collections import defaultdict
from urllib.parse import urlparse, parse_qs
import os
import json
try:
    from . import __version__
except ImportError:
    __version__ = "0.1.0"


class TokenBucketRateLimiter:
    """Token-bucket rate limiter shared across all threads."""

    def __init__(self, rate: float):
        self.rate = rate
        self.tokens = rate
        self.max_tokens = rate
        self.last_refill = time.monotonic()
        self.lock = Lock()

    def acquire(self):
        while True:
            with self.lock:
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.tokens = min(self.max_tokens, self.tokens + elapsed * self.rate)
                self.last_refill = now

                if self.tokens >= 1:
                    self.tokens -= 1
                    return

            time.sleep(0.1)

class colors:
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ENDC = '\033[0m'

def showBanner():
    import sys
    banner = rf"""{colors.CYAN}{colors.BOLD}
    ____        __          _____           __         
   / __ \____  / /_  ____  / __(_)___  ____/ /__  _____
  / /_/ / __ \/ __ \/ __ \/ /_/ / __ \/ __  / _ \/ ___/
 / _, _/ /_/ / /_/ / /_/ / __/ / / / / /_/ /  __/ /    
/_/ |_|\____/_____/\____/_/ /_/_/ /_/\____/\___/_/{colors.ENDC}
{colors.DIM}  v{__version__} - Mine historical robots.txt from Wayback Machine{colors.ENDC}
{colors.PURPLE}  github.com/Spix0r{colors.ENDC}
"""
    print(banner, file=sys.stderr)

def log(debug, level, message):
    if not debug:
        return
    import sys
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime("%H:%M:%S")
    
    if level == "info":
        tag_color = colors.CYAN
        tag = "INFO"
    elif level == "warn":
        tag_color = colors.WARNING
        tag = "WARN"
    elif level == "error":
        tag_color = colors.ERROR
        tag = "ERR "
    elif level == "retry":
        tag_color = colors.WARNING
        tag = "TRY "
    elif level == "ok":
        tag_color = colors.GREEN
        tag = " OK "
    else:
        tag_color = colors.CYAN
        tag = "DEBUG"
    
    print(f"{colors.DIM}[{formatted_time}]{colors.ENDC} {tag_color}{colors.BOLD}[{tag}]{colors.ENDC} {message}", file=sys.stderr)

def setup_argparse():
    parser = argparse.ArgumentParser(
        prog='robofinder',
        description=f'{colors.CYAN}{colors.BOLD}Robofinder{colors.ENDC} v{__version__} - Mine historical robots.txt from Wayback Machine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""{colors.DIM}examples:{colors.ENDC}
  robofinder -u https://example.com
  robofinder -u https://example.com -f json -o results
  robofinder -u domains.txt -c | httpx -silent
  robofinder -u https://example.com -r 1 --cooldown 30"""
    )
    
    parser.add_argument('--url', '-u', dest='url', type=str, required=True,
                        help='Target URL or file with one URL per line')
    
    output = parser.add_argument_group(f'{colors.GREEN}output{colors.ENDC}')
    output.add_argument('--output', '-o', dest='output', nargs='?', const=True, default=None,
                        help='Output to terminal (no value) or save to file (with value)')
    output.add_argument('--format', '-f', dest='format', type=str, default='txt',
                        choices=['txt', 'json', 'both'],
                        help='Output format (default: txt)')
    output.add_argument('-c', action="store_true", default=False,
                        help='Prefix paths with target URL (full URLs)')
    output.add_argument('-p', action="store_true", default=False,
                        help='Extract URL parameters from historical paths')
    
    config = parser.add_argument_group(f'{colors.GREEN}config{colors.ENDC}')
    config.add_argument('--threads', '-t', dest='threads', default=1, type=int,
                        help='Concurrent threads (default: 1)')
    config.add_argument('--rate-limit', '-r', dest='rate_limit', default=2.0, type=float,
                        help='Max requests/sec to Archive.org (default: 2.0)')
    config.add_argument('--cooldown', dest='cooldown', default=10, type=int,
                        help='Seconds to wait between domains (default: 10)')
    config.add_argument('--silent', '-s', action="store_true", default=False,
                        help='Suppress the banner')
    config.add_argument("--debug", action="store_true", default=False,
                        help='Enable verbose debug output')
    
    return parser.parse_args()

def extract(response):
    robots = []
    final = []
    regex = r"Allow:\s*\S+|Disallow:\s*\S+|Sitemap:\s*\S+"
    directive_regex = re.compile(r"(allow|disallow|user[-]?agent|sitemap|crawl-delay):[ \t]*(.*)", re.IGNORECASE)
    
    lines = re.findall(regex, response)
    for line in lines:
        d = directive_regex.findall(line)
        if d:
            robots.append(d)
    
    for i in robots:
        if i and i[0]:
            final.append(i[0][1].strip())
    return final

def get_all_links(base_url):
    base_url = base_url.rstrip('/')
    robots_url = f"{base_url}/robots.txt"
    cdx_url = f"https://web.archive.org/cdx/search/cdx?url={robots_url}&output=json&fl=timestamp,original&filter=statuscode:200&collapse=digest"

    log(args.debug, "info", f"Querying CDX for {robots_url}")

    max_retries = 7
    retry_count = 0

    while retry_count < max_retries:
        try:
            rate_limiter.acquire()
            resp = requests.get(cdx_url, timeout=(10, 120))
            resp.raise_for_status()
            obj = resp.json()
            log(args.debug, "ok", f"Found {len(obj)-1} snapshots")

            url_list = []
            for i in obj[1:]:
                if len(i) >= 2:
                    url_list.append(f"https://web.archive.org/web/{i[0]}if_/{i[1]}")

            return list(dict.fromkeys(url_list))

        except requests.exceptions.Timeout as e:
            backoff = min(60, (2 ** retry_count) + random.uniform(0, 2))
            log(args.debug, "retry", f"CDX timeout - retry in {backoff:.0f}s ({retry_count + 1}/{max_retries})")
            time.sleep(backoff)
            retry_count += 1

        except requests.exceptions.SSLError as e:
            backoff = min(60, (2 ** retry_count) + random.uniform(0, 2))
            log(args.debug, "retry", f"SSL error - retry in {backoff:.0f}s ({retry_count + 1}/{max_retries})")
            time.sleep(backoff)
            retry_count += 1

        except requests.exceptions.ConnectionError as e:
            backoff = min(60, (2 ** retry_count) + random.uniform(0, 2))
            log(args.debug, "retry", f"Connection error - retry in {backoff:.0f}s ({retry_count + 1}/{max_retries})")
            time.sleep(backoff)
            retry_count += 1

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                retry_after = int(e.response.headers.get('Retry-After', min(60, 5 ** retry_count)))
                log(args.debug, "warn", f"Rate limited (429) - waiting {retry_after}s")
                time.sleep(retry_after)
                retry_count += 1
            else:
                log(args.debug, "error", f"HTTP {e.response.status_code} on CDX")
                return []

        except Exception as e:
            log(args.debug, "error", f"CDX failed: {e}")
            return []

    log(args.debug, "error", f"Gave up on CDX after {max_retries} retries for {base_url}")
    return []

thread_local = local()
rate_limiter = None

def get_session():
    if not hasattr(thread_local,'session'):
        thread_local.session = requests.Session()
    return thread_local.session

def fetchFiles(url: str):
    global rate_limiter
    session = get_session()
    max_retries = 7
    retry_count = 0

    while retry_count < max_retries:
        try:
            rate_limiter.acquire()
            log(args.debug, "info", f"GET {url}")
            response = session.get(url, timeout=(10, 90))

            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', min(60, 5 ** retry_count)))
                log(args.debug, "warn", f"429 {url} - waiting {retry_after}s")
                time.sleep(retry_after)
                retry_count += 1
                continue

            log(args.debug, "ok", f"{response.status_code} {url}")
            return response

        except requests.exceptions.RequestException as e:
            backoff = min(60, (2 ** retry_count) + random.uniform(0, 2))
            log(args.debug, "retry", f"Failed {url} - retry in {backoff:.0f}s")
            time.sleep(backoff)
            retry_count += 1

    log(args.debug, "error", f"Gave up on {url} after {max_retries} retries")
    return None

def concatinate(base_url, paths):
    concatinated = []
    try:
        for i in paths:
            if not i or i.strip() == "": continue
            i = i.strip()
            if validators.url(i):
                concatinated.append(i)
            else:
                if i[0] == "/":
                    concatinated.append(base_url+i)
                else:
                    concatinated.append(base_url+"/"+i)
    except Exception as e:
        log(args.debug, "error", f"Concat error: {e}")

    return concatinated
           
def extractParams(urls):
    result = []
    for url in urls:
        try:
            parsed_url = urlparse(url)
            captured_value = parse_qs(parsed_url.query)
            if captured_value:
                result += list(captured_value.keys())
        except Exception as e:
            log(args.debug, "error", f"Param extract error: {e}")
    return list(set(result))

def format_txt(grouped_results, silent=False):
    lines = []
    for domain, data in grouped_results.items():
        if silent:
            for path in data["paths"]:
                lines.append(path)
        else:
            lines.append("=" * 70)
            lines.append(f"[ {domain} ]  →  {len(data['paths'])} paths")
            lines.append("=" * 70)
            for path in data["paths"]:
                lines.append(path)
            lines.append("")
    return "\n".join(lines)

def format_json(grouped_results):
    output_data = {
        domain: {
            "original_url": data["original_url"],
            "count": len(data["paths"]),
            "paths": data["paths"]
        }
        for domain, data in grouped_results.items()
    }
    return json.dumps(output_data, ensure_ascii=False, indent=2)

def save_results_by_domain(grouped_results, output_dir="output"):
    os.makedirs(output_dir, exist_ok=True)
    for domain, data in grouped_results.items():
        file_path = os.path.join(output_dir, f"{domain}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            for item in data["paths"]:
                f.write(item + "\n")

def main():
    global args, rate_limiter
    start = time.time()
    if '--silent' not in sys.argv and '-s' not in sys.argv:
        showBanner()
    args = setup_argparse()
    rate_limiter = TokenBucketRateLimiter(args.rate_limit)

    log(args.debug, "info", "Starting RoboFinder")

    input_urls = []
    if os.path.isfile(args.url):
        with open(args.url, 'r', encoding='utf-8') as f:
            input_urls = [line.strip() for line in f if line.strip()]
    else:
        input_urls = [args.url]

    if not input_urls:
        log(args.debug, "error", "No URLs provided")
        return

    grouped_results = defaultdict(lambda: {"paths": [], "original_url": ""})

    for base_url in input_urls:
        log(args.debug, "info", f"Processing {base_url}")
        domain = urlparse(base_url).netloc or base_url

        if not domain:
            domain = "unknown"

        grouped_results[domain]["original_url"] = base_url

        url_list = get_all_links(base_url)
        if not url_list:
            continue

        log(args.debug, "info", f"Fetching {len(url_list)} snapshots...")
        responses = []
        for url in url_list:
            resp = fetchFiles(url)
            if resp and resp.text:
                responses.append(resp.text)

        for resp in responses:
            grouped_results[domain]["paths"].extend(extract(resp))

        log(args.debug, "ok", f"{domain}: {len(grouped_results[domain]['paths'])} paths")

        if base_url != input_urls[-1]:
            log(args.debug, "info", f"Cooling down {args.cooldown}s...")
            time.sleep(args.cooldown)

    for domain in grouped_results:
        grouped_results[domain]["paths"] = list(dict.fromkeys(grouped_results[domain]["paths"]))

    if args.c or args.p:
        for domain in grouped_results:
            if args.c:
                grouped_results[domain]["paths"] = concatinate(
                    grouped_results[domain]["original_url"], 
                    grouped_results[domain]["paths"]
                )
            if args.p:
                grouped_results[domain]["paths"] = extractParams(grouped_results[domain]["paths"])

    silent = args.silent
    # ====================== Output Handling ======================
    if args.output is True:
        # -o with no value → terminal
        if args.format in ['txt', 'both']:
            print(format_txt(grouped_results, silent))
        if args.format in ['json', 'both']:
            print(format_json(grouped_results))
    elif args.output:
        # -o with value → file
        base_name = args.output
        if not base_name.endswith('.txt') and not base_name.endswith('.json'):
            if args.format == 'json':
                base_name += '.json'
            else:
                base_name += '.txt'

        if args.format in ['txt', 'both']:
            txt_file = base_name if base_name.endswith('.txt') else base_name.rsplit('.', 1)[0] + '.txt'
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(format_txt(grouped_results))
            log(True, "ok", f"Saved: {txt_file}")

        if args.format in ['json', 'both']:
            json_file = base_name if base_name.endswith('.json') else base_name.rsplit('.', 1)[0] + '.json'
            with open(json_file, 'w', encoding='utf-8') as f:
                f.write(format_json(grouped_results))
            log(True, "ok", f"Saved: {json_file}")
    else:
        # no -o → terminal
        if args.format in ['txt', 'both']:
            print(format_txt(grouped_results, silent))
        if args.format in ['json', 'both']:
            print(format_json(grouped_results))

    end = time.time()
    log(args.debug, "info", f"Done in {end - start:.1f}s - {len(grouped_results)} domains")

if __name__ == "__main__":
    main()