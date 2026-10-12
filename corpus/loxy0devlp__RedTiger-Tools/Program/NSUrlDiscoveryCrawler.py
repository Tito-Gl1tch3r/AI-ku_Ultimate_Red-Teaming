# Copyright (c) RedTiger by Loxy0devlp
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from Config.Utils import *
from Program.Utils.NetworkScanningUtils import *

def UrlValidExtension(url):
    return re.search(r"\.(html|xhtml|php|js|css)$", url) or not re.search(r"\.\w+$", url)

def UrlClean(url):
    stop_chars = ["\"", "}", "]", "{", "["]
    for char in stop_chars:
        if char in url:
            url = url.split(char)[0]
    url = url.replace("\\", "")
    return url

def ExtractLinks(base_url, domain, tags, all_links, attr_list=("href", "src", "action")):
    extracted = []
    for tag in tags:
        for attr in attr_list:
            value = tag.get(attr)
            if value:
                full_url = urllib.parse.urljoin(base_url, value)
                full_url = UrlClean(full_url) 
                if domain in full_url and UrlValidExtension(full_url) and full_url not in all_links:
                    all_links.add(full_url)
                    extracted.append(full_url)
    return extracted

def ExtractLinksFromScripts(scripts, domain, all_links):
    extracted = []
    for script in scripts:
        if script.string:
            for url in re.findall(r"(https?://\S+)", script.string):
                url = UrlClean(url)
                if domain in url and UrlValidExtension(url) and url not in all_links:
                    all_links.add(url)
                    extracted.append(url)
    return extracted

def FindSecretUrls(url, domain, session, all_links, http_timeout):
    try:
        response = session.get(url, timeout=http_timeout)
        if response.status_code != 200:
            return

        content_type = response.headers.get("Content-Type", "").lower()
        if "xml" in content_type: soup = bs4.BeautifulSoup(response.content, "lxml-xml")
        else:
            warnings.filterwarnings("ignore", category=bs4.XMLParsedAsHTMLWarning)
            soup = bs4.BeautifulSoup(response.content, "html.parser")
        tags = soup.find_all(["a", "link", "script", "img", "iframe", "button", "form"])
        extracted_links = ExtractLinks(url, domain, tags, all_links)
        extracted_links += ExtractLinksFromScripts(soup.find_all("script"), domain, all_links)
        for link in extracted_links: Add(f"URL found: {white + str(link)}")
    except: pass

def FindAllSecretUrls(url, domain, session, all_links, http_timeout):
    FindSecretUrls(url, domain, session, all_links, http_timeout)
    visited = set()
    while True:
        new_links = [link for link in all_links if link not in visited]
        if not new_links:
            break
        for link in new_links:
            try:
                if session.get(link).status_code == 200:
                    FindSecretUrls(link, domain, session, all_links, http_timeout)
                visited.add(link)
            except: visited.add(link)

def UrlDiscoveryCrawler(target=None, mode=None, output=None, http_timeout=None, http_proxy=None, useragent=None, cookie=None):
    Title("URL Discovery Crawler")

    if not target: target = Input("Target [-t] -> ")
    detect_target = DetectTarget(target)

    if not detect_target in ["url", "url/page", "domain", "domain/page", "localhost:port", "localhost:port/page", "ip:port", "ip:port/page"]: ErrorUrlDomainLocalhostportIpport()
    elif any(bad in target for bad in blacklists): ErrorTarget()

    if not has_cli_args: 
        http_timeout = Input(f"Max HTTP timeout [-HT] (default: {str(default_http_timeout)}) -> ")
        http_proxy   = Input(f"HTTP proxy [-HP] (default: {str(default_http_proxy)}) -> ")
        useragent    = Input(f"User-Agent [-u] (for random: random, default: {str(default_useragent)}) -> ")
        cookie       = Input(f"Cookie [-c] (default: {str(default_cookie)}) -> ")

    if not http_proxy: http_proxy = default_http_proxy
    if not useragent : useragent  = default_useragent
    if not cookie    : cookie     = default_cookie

    try:
        if not http_timeout: http_timeout = default_http_timeout
        else: http_timeout = float(http_timeout)
        Info(f"Max HTTP timeout: {white}{str(http_timeout)}s")
    except (ValueError, TypeError): ErrorTimeout()

    session, proxies, cookie, useragent = EnableHttpProxyAndUserAgentAndCookie(http_proxy=http_proxy, useragent=useragent, cookie=cookie, http_timeout=http_timeout)

    json_data = {
        "Parameters": {
            "HTTP timeout": http_timeout if http_timeout else None,
            "HTTP proxy": http_proxy if http_proxy else None,
            "User-agent": useragent if useragent else None,
            "Cookie": cookie if cookie else None,
        }
    }

    Wait("Information scanning..")
    url, response, status_url, latency_url, json_format = TargetGetUrlAndStatusAndLatency(target.strip(), session, http_timeout)
    if url and status_url != "404":
        MergeJson(json_data, json_format)
        domain, json_format = TargetGetDomain(url)
        MergeJson(json_data, json_format)
        all_links = set()

        if not mode:
            print(f"""
  {BEFORE}01{AFTER + white} Only the web page
  {BEFORE}02{AFTER + white} All website
            """)
            mode = Input("Scan mode [-m] -> ")

        Wait("Scanning..")
        state = {"stop": False}
        StartThread(StatsPressed, state, time_start=time.time())
        if mode in ("1", "01", "onlypage"): 
            json_data["Parameters"]["Mode"] = "onlypage"
            FindSecretUrls(url, domain, session, all_links, http_timeout)
        elif mode in ("2", "02", "allwebsite"): 
            json_data["Parameters"]["Mode"] = "allwebsite"
            FindAllSecretUrls(url, domain, session, all_links, http_timeout)
        else: 
            ErrorMode()

        state["stop"] = True
        Info(f"Total URLs found: {white + str(len(all_links))}")
        MergeJson(json_data, json.dumps({"URLs found": list(all_links)}, indent=4))
        if output in (True, None): SaveJsonToFile(json_data, f"Result_URLFinderScanner_{target}", json_output=output)
    else: ErrorTarget()
    Continue()
    Reset()