# Copyright (c) RedTiger by Loxy0devlp
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

import sys
try:
    import os, datetime, subprocess, ctypes, time, colorama, random, socket, socks, requests, threading, argparse, json
    import keyboard, concurrent.futures, urllib, urllib.parse, urllib3, ipaddress, re, errno, select, collections, warnings
    import hashlib, OpenSSL, struct, ipwhois, dns.resolver, base64, piexif, exifread, PIL.Image, mutagen, stat, ssl
    import bs4, webbrowser, shutil, tempfile, zipfile, tarfile, sqlite3, pathlib, wave, contextlib, fitz, lxml, lxml.html
    import phonenumbers, phonenumbers.geocoder, phonenumbers.carrier, phonenumbers.timezone, whois, smtplib, string, logging
    import instaloader, math, zlib, importlib.util
except Exception as e:
    print(f"\nModules of the python library required for RedTiger are not installed, make sure you have correctly installed python and have launched the \"setup.py\" file which will install all the necessary modules.")
    sys.exit(f"Error: {e}")

try:    os_name     = "Windows" if sys.platform.startswith("win") else "Linux" if sys.platform.startswith("linux") else "Unknown"
except: os_name     = "Unknown"
try:    os_username = os.getlogin()
except: os_username = "username"

path_folder_tool                        = os.path.abspath(__file__).split(os.sep + "Config" + os.sep)[0]
path_folder_data                        = os.path.join(path_folder_tool,   "Data")
path_folder_plugins                     = os.path.join(path_folder_tool,   "Plugins")
path_folder_ouput                       = os.path.join(path_folder_tool,   "Ouput")
path_folder_ouput_file_metadata_scanner = os.path.join(path_folder_ouput,  "Files_FileMetadataScanner")
path_folder_config                      = os.path.join(path_folder_tool,   "Config")
path_file_credits                       = os.path.join(path_folder_config, "Credits.json")
path_file_version_settings              = os.path.join(path_folder_config, "UserSettings.json")
path_file_tool                          = os.path.join(path_folder_tool,   "redtiger.py")
path_file_useragent                     = os.path.join(path_folder_data,   "UserAgents.txt")
path_file_ports                         = os.path.join(path_folder_data,   "Ports.json")
path_file_default_ports                 = os.path.join(path_folder_data,   "DefaultPorts.json")
path_file_default_parameters            = os.path.join(path_folder_data,   "DefaultParameters.json")
path_file_vulnerability_errors          = os.path.join(path_folder_data,   "VulnerabilityErrors.json")
path_file_vulnerability_payloads        = os.path.join(path_folder_data,   "VulnerabilityPayloads.json")
path_file_vulnerability_sensitive_paths = os.path.join(path_folder_data,   "VulnerabilitySensitivePaths.json")
path_file_username_tracker_plateforms   = os.path.join(path_folder_data,   "UsernameTrackerPlateforms.json")

def StrToBool(value): return value == "True"

with open(path_file_credits,                       "r", encoding="utf-8") as file: data_credits                       = json.load(file)
with open(path_file_version_settings,              "r", encoding="utf-8") as file: data_version_settings              = json.load(file)
with open(path_file_default_parameters,            "r", encoding="utf-8") as file: data_default_parameters            = json.load(file)
with open(path_file_ports,                         "r", encoding="utf-8") as file: data_ports                         = json.load(file)
with open(path_file_default_ports,                 "r", encoding="utf-8") as file: data_default_ports                 = json.load(file)
with open(path_file_vulnerability_errors,          "r", encoding="utf-8") as file: data_vulnerability_errors          = json.load(file)
with open(path_file_vulnerability_payloads,        "r", encoding="utf-8") as file: data_vulnerability_payloads        = json.load(file)
with open(path_file_vulnerability_sensitive_paths, "r", encoding="utf-8") as file: data_vulnerability_sensitive_paths = json.load(file)
with open(path_file_username_tracker_plateforms,   "r", encoding="utf-8") as file: data_username_tracker_plateforms   = json.load(file)

tool_name, tool_version, tool_license, tool_github, developer, website, telegram, gunslol = (
    data_credits.get("tool_name", None),
    data_credits.get("tool_version", None),
    data_credits.get("tool_license", None),
    data_credits.get("tool_github", None),
    data_credits.get("developer", None),
    data_credits.get("website", None),
    data_credits.get("telegram", None),
    data_credits.get("gunslol", None),
)

version_decorated, version_interface = (
    StrToBool(data_version_settings.get("version_decorated", None)),
    StrToBool(data_version_settings.get("version_interface", None)),
)

default_useragent, default_http_timeout, default_socket_timeout, default_icmp_timeout, default_tcp_icmp_timeout, default_interval, default_port, default_bytes, default_protocol, default_http_proxy, default_socket_proxy, default_cookie, default_instagram_session_id, max_port, max_bytes = (
    str(data_default_parameters.get("default_useragent", None)).replace("%TOOL_NAME%", tool_name).replace("%TOOL_VERSION%", tool_version),
    data_default_parameters.get("default_http_timeout", None),
    data_default_parameters.get("default_socket_timeout", None),
    data_default_parameters.get("default_icmp_timeout", None),
    data_default_parameters.get("default_tcp_icmp_timeout", None),
    data_default_parameters.get("default_interval", None),
    data_default_parameters.get("default_port", None),
    data_default_parameters.get("default_bytes", None),
    data_default_parameters.get("default_protocol", None),
    data_default_parameters.get("default_http_proxy", None),
    data_default_parameters.get("default_socket_proxy", None),
    data_default_parameters.get("default_cookie", None),
    data_default_parameters.get("default_instagram_session_id", None),
    data_default_parameters.get("max_port", None),
    data_default_parameters.get("max_bytes", None),
)

if not version_decorated:
    red, light_red, white, green, blue, yellow, reset = (
        "", "", "", "", "", "", "",
    )
else:
    colorama.init()
    color = colorama.Fore
    red, light_red, white, green, blue, yellow, reset = (
        color.RED, color.LIGHTRED_EX, color.WHITE, color.GREEN, color.BLUE, color.YELLOW, color.RESET
    )

BEFORE = f'{red}[{white}'
AFTER  = f'{red}]'

INPUT = f'{BEFORE}>{AFTER}'
INFO  = f'{BEFORE}!{AFTER}'
ERROR = f'{BEFORE}x{AFTER}'
ADD   = f'{BEFORE}+{AFTER}'
WAIT  = f'{BEFORE}~{AFTER}'

thread_status = True
affirmative   = ["y", "ye", "yes", "yeah", "yep", "ok", "okay", "o", "ou", "oui", "true", "1"]
blacklists    = ["0.0.0.0"]
api_ip_lookup = "ip-api.com"

def HasCliArgs(): return len(sys.argv) > 1
has_cli_args = HasCliArgs()

def Hour():
    return datetime.datetime.now().strftime('%H:%M:%S')

def Info(message):
    return print(f"{BEFORE}{Hour()}{AFTER} {INFO} {message}{reset}")

def Error(message):
    return print(f"{BEFORE}{Hour()}{AFTER} {ERROR} {message}{reset}")

def Add(message):
    return print(f"{BEFORE}{Hour()}{AFTER} {ADD} {message}{reset}")

def Wait(message):
    return print(f"{BEFORE}{Hour()}{AFTER} {WAIT} {message}{reset}")

def Input(message):
    return input(f"{BEFORE}{Hour()}{AFTER} {INPUT} {message}{reset}")

def Title(title):
    if os_name == "Windows": ctypes.windll.kernel32.SetConsoleTitleW(f"{tool_name} v{tool_version} - {title}")
    elif os_name == "Linux": sys.stdout.write(f"\x1b]2;{tool_name} v{tool_version} - {title}\x07")

def Clear():
    if os_name == "Windows": subprocess.run("cls",   shell=True)
    elif os_name == "Linux": subprocess.run("clear", shell=True)

def Start():
    if os_name == "Windows": subprocess.run(['python',  path_file_tool])
    elif os_name == "Linux": subprocess.run(['python3', path_file_tool])

def Reset():
    if version_interface and not has_cli_args: Start()
    else: sys.exit(0)

def Slow(text):
    if not version_decorated or not version_interface or has_cli_args: print(text)
    else:
        for ligne in text.split('\n'):
            print(ligne)
            time.sleep(0.03)

def Continue():
    if version_interface and not has_cli_args: Input("Press to continue -> ")
    else: return

class RedTigerArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print()
        Error(f"Error: {white + message}")
        Info(f"Use {white}--help{red} or {white}-h{red} to see the available options.")
        Reset()

def IsAdmin():
    if os_name == "Windows":
        try: return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except: return False
    elif os_name == "Linux":
        try: return os.geteuid() == 0
        except: return False

def RunSpeed(state, ctx, json_data, keys, func):
    result = func()
    *values, json_format = result
    for k, v in zip(keys, values): ctx[k] = v
    MergeJson(json_data, json_format)
    state["completed"] += 1

def StatsPressed(state, time_start=None):
    global thread_status
    if os_name == "Linux" and not IsAdmin():
        Info("To be able to view progress statistics, administrator mode is required.")
        return
    Info(f"Press \"{white}s{red}\" to display progress statistics.")
    while thread_status:
        if keyboard.is_pressed("s"):
            text = f"Status: {white}in progress.. "
            if 'message' in state: text += f"{state['message']} "
            if "completed" in state and "completed_total" in state: text += f"{red}Completed: {white}{state['completed']}/{state['completed_total']} "
            if time_start: text += f"{red}Time: {white}{(time.time() - time_start):.2f}s "
            Info(text)
        if "stop" in state:
            if state["stop"] == True:
                thread_status = False
                break
        if "completed" in state and "completed_total" in state:
            if int(state["completed"]) >= int(state["completed_total"]):
                thread_status = False
                break
        time.sleep(0.1)
    thread_status == True

def StartThread(function, *args, **kwargs):
    thread = None
    try: 
        thread = threading.Thread(target=function, daemon=True, args=args, kwargs=kwargs)
        thread.start()
    except Exception as e: ErrorUnknown(e)
    return thread

def MergeJson(json_data, new_json):
    if not new_json: return json_data
    if isinstance(new_json, str):
        try: new_json = json.loads(new_json)
        except: new_json = None
    if isinstance(new_json, dict):
        for k, v in new_json.items():
            if v is not None: json_data[k] = v
    return json.dumps(json_data, indent=4)

def SaveJsonToFile(json_data, filename, json_output=None):
    for char in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']: filename = filename.replace(char, "_")
    path_json_file = os.path.join(path_folder_ouput, filename+".json")
    if json_output == None: json_output = Input(f"Do you want to create a JSON file ? [-o] (y/n) -> ")
    if str(json_output).strip().lower() in affirmative:
        if isinstance(json_data, str):
            try: json_data = json.loads(json_data)
            except: json_data = {}
        try:
            with open(path_json_file, "w", encoding="utf-8") as file: 
                json.dump({f"{tool_name} v{tool_version}": json_data}, file, indent=4)
            Info(f"JSON file created: {white + path_json_file}")
        except Exception as e:
            ErrorUnknown(e)

def CheckUpdate():
    url = "https://" + tool_github.replace("github.com/", "raw.githubusercontent.com/") + "/main/Config/Credits.json"
    try:
        response    = requests.get(url, timeout=default_http_timeout)
        response.raise_for_status()
        data        = response.json()
        version     = data.get("tool_version", None)
        if version is None: return None
        return version != tool_version
    except Exception: return None
    
def ErrorUnknown(error):
    Error(error)
    Continue()
    Reset()

def ErrorChoiceStart():
    print()
    Error("Invalid choice.")
    time.sleep(1)

def ErrorChoice():
    Error("Invalid choice.")
    Continue()
    Reset()

def ErrorUrlDomainLocalhostportIpport():
    Error("Invalid target, example: [http[s]://]example.com / [http[s]://]localhost:0000 / [http[s]://]0.0.0.0:0000")
    Continue()
    Reset()

def ErrorUrlDomainLocalhostIp():
    Error("Invalid target, example: [http[s]://]example.com / [http[s]://]localhost[:0000] / [http[s]://]0.0.0.0[:0000]")
    Continue()
    Reset()

def ErrorIp():
    Error("Invalid target, example: ipv4 / ipv6")
    Continue()
    Reset()

def ErrorCidr():
    Error("Invalid CIDR, exemple: ipv4/24 / ipv6/64")
    Continue()
    Reset()

def ErrorTarget():
    Error("The target does not exist.")
    Continue()
    Reset()

def ErrorPort():
    Error("Invalid port.")
    Continue()
    Reset()

def ErrorFormat():
    Error("Invalid format.")
    Continue()
    Reset()

def ErrorMode():
    Error("Invalid mode.")
    Continue()
    Reset()

def ErrorBytes():
    Error(f"Invalid bytes. (max: {max_bytes})")
    Continue()
    Reset()

def ErrorNumber():
    Error("Invalid number.")
    Continue()
    Reset()

def ErrorTimeout():
    Error("Invalid timeout.")
    Continue()
    Reset()

def ErrorInterval():
    Error("Invalid interval.")
    Continue()
    Reset()

def ErrorPath():
    Error("Invalid path.")
    Continue()
    Reset()

def ErrorSocketProxy():
    Error("Invalid socket proxy.")
    Continue()
    Reset()

def ErrorHttpProxy():
    Error("Invalid HTTP proxy.")
    Continue()
    Reset()

def ErrorAssignedSocketProxy():
    Error("The socket proxy could not be assigned.")
    Continue()
    Reset()

def ErrorNumberFormat():
    Error("Invalid number or missing region.")
    Continue()
    Reset()

def ErrorEmail():
    Error("Invalid email.")
    Continue()
    Reset()

def ErrorSession():
    Error("Invalid session.")
    Continue()
    Reset()

def ValidUserAgent(useragent):
    if useragent in ("random", "rdm"):
        Wait("Searching for a valid user-agent..")
        lines = open(path_file_useragent,"r",encoding="utf-8").read().splitlines()
        useragent = random.choice(lines).strip() if lines else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5414.120 Safari/537.36"
        Info(f"Selected user-agent: {white}{useragent}")
    elif useragent: Info(f"User-agent: {white}{useragent}")
    else: 
        useragent = default_useragent
        Info(f"User-agent: {white}{useragent}")
    return useragent

def ValidHttpProxy(http_proxy, http_timeout=default_http_timeout):
    if http_proxy:
        Wait("Testing the HTTP proxy..")
        try:
            response = requests.get("http://api.ipify.org", proxies={"http": http_proxy, "https": http_proxy}, timeout=http_timeout)
            if response.status_code == 200:
                Info(f"HTTP proxy: {white}{http_proxy}")
                return http_proxy
        except: pass
        ErrorHttpProxy()
    else: Info(f"HTTP proxy: {white}None")
    return None

def ValidSocketProxy(socket_proxy, socket_timeout=default_socket_timeout):
    if socket_proxy:
        Wait("Testing the socket proxy..")
        for scheme in ("socks5", "socks4"):
            try:
                proxies = {"http":  f"{scheme}://{socket_proxy}", "https": f"{scheme}://{socket_proxy}"}
                response = requests.get("http://api.ipify.org", proxies=proxies, timeout=socket_timeout)
                if response.status_code == 200:
                    Info(f"Socket proxy: {white}{socket_proxy}")
                    return socket_proxy
            except: continue
        ErrorSocketProxy()
    else: Info(f"Socket proxy: {white}None")
    return None

def EnableHttpProxyAndUserAgentAndCookie(http_proxy=None, useragent=None, cookie=None, enable_cookie=True, http_timeout=default_http_timeout):
    proxies = None
    useragent  = ValidUserAgent(useragent)
    proxy      = ValidHttpProxy(http_proxy, http_timeout)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    session        = requests.Session()
    session.verify = False
    if useragent: 
        headers = {"User-Agent": useragent}
        session.headers.update(headers)
    if cookie and enable_cookie:
        Info(f"Cookie: {white}{cookie}")
        session.headers.update({"Cookie": cookie})
    else: 
        if enable_cookie: Info(f"Cookie: {white}None")
    if proxy: 
        proxies = {"http": proxy, "https": proxy}
        session.proxies.update(proxies)
    return session, proxies, cookie, useragent

def EnableSocketProxy(socket_proxy=None, socket_timeout=default_socket_timeout, log=True):
    try:
        proxy = ValidSocketProxy(socket_proxy, socket_timeout)
        if proxy:
            host, port = proxy.split(":")
            port = int(port)
            socks.set_default_proxy(socks.SOCKS5, host, port, rdns=True)
            socket.socket = socks.socksocket
            return True
        else: return False
    except: 
        if log: ErrorAssignedSocketProxy()
        return False

def MainColor(text):
    if not version_decorated: return text
    else:
        colorama.deinit()
        def TextColor(r, g, b): return f"\033[38;2;{r};{g};{b}m"

        start_color = (168, 5, 5)  
        end_color = (255, 118, 118)
        num_steps = 9
        colors = []

        for i in range(num_steps):
            r = start_color[0] + (end_color[0] - start_color[0]) * i // (num_steps - 1)
            g = start_color[1] + (end_color[1] - start_color[1]) * i // (num_steps - 1)
            b = start_color[2] + (end_color[2] - start_color[2]) * i // (num_steps - 1)
            colors.append((r, g, b))

        colors += list(reversed(colors[:-1]))  
        gradient_chars = "_|\\/]()┌─└"
        lines = text.split('\n')
        result = []

        for i, line in enumerate(lines):
            for j, char in enumerate(line):
                if char in gradient_chars:
                    color_index = (i + j) % len(colors)
                    color = colors[color_index]
                    result.append(TextColor(*color) + char + "\033[0m")
                else:
                    result.append(char)
            if i < len(lines) - 1:
                result.append('\n')
        colorama.init()
        return ''.join(result)

banner_redtiger = r"""
                              __________            ______________ __                     
                              \______   \ ____   __| _/\__    ___/|__| ____   ___________ 
                               |       _// __ \ / __ |   |    |   |  |/ ___\_/ __ \_  __ \
                               |    |   \  ___// /_/ |   |    |   |  / /_/  |  ___/|  | \/
                               |____|___/\_____|_____|   |____|   |__\___  / \_____|__|   
                                                                    /_____/               
""" + f"""                                                   {f" {green}Update available !" if CheckUpdate() else ""}
                                          {white}{tool_github}"""
