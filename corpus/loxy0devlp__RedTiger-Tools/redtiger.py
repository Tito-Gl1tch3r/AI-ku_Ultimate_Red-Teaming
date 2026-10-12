# Copyright (c) RedTiger by Loxy0devlp
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from Config.Utils import *

try:
    from Program.NSAdvancedScanner       import AdvancedScanner
    from Program.NSVulnerabilityScanner  import VulnerabilityScanner
    from Program.NSPortScanner           import PortScanner
    from Program.NSUrlDiscoveryCrawler   import UrlDiscoveryCrawler
    from Program.NSIpPinger              import IpPinger
    from Program.NSHostDiscovery         import HostDiscovery

    from Program.ODorkingQueryEngine     import DorkingQueryEngine
    from Program.OWalletTracker          import WalletTracker
    from Program.OUsernameTracker        import UsernameTracker
    from Program.OEmailTracker           import EmailTracker
    from Program.OEmailLookup            import EmailLookup
    from Program.OIpLookup               import IpLookup
    from Program.OPhoneNumerLookup       import PhoneNumerLookup
    from Program.OInstagramProfileLookup import InstagramProfileLookup

    from Program.UFileMetadataScanner    import FileMetadataScanner
    from Program.UFileMetadataDeleter    import FileMetadataDeleter
    from Program.UWebsiteCloner          import WebsiteCloner

    from Program.THelp                   import Help
    from Program.TVersion                import Version
    from Program.TSettingsUpdate         import SettingsUpdate
except Exception as e: 
    Error(f"Error while loading programs: {white}{e}")
    sys.exit()

def InjectPlugins(options_list):
    plugins = {}

    if os.path.exists(path_folder_plugins):
        for file in os.listdir(path_folder_plugins):
            if file == "Example.py": continue
            if not file.endswith(".py"): continue

            path        = os.path.join(path_folder_plugins, file)
            module_name = file[:-3]

            try:
                spec   = importlib.util.spec_from_file_location(module_name, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if hasattr(module, "Register"):
                    plugin_data = module.Register()
                    plugins[module_name] = plugin_data
            except Exception: continue

    if not plugins: return options_list
    existing_ids = set(options_list.keys())
    next_id      = max(existing_ids) + 1 if existing_ids else 1

    for plugin in plugins.values():
        name        = plugin.get("name", "Unknown")
        description = plugin.get("description", "")
        function    = plugin.get("function", None)
        arguments   = plugin.get("arguments", {})

        while next_id in existing_ids: next_id += 1
        options_list[next_id] = (name, description, "Plugins", function, arguments)
        existing_ids.add(next_id)
        next_id += 1

    return options_list

def Options():
    options_list = {
    #   Number   Name                        Description                                                               Category      Function                Argument
        1     : ("Advanced Scanner",         "Advanced scanning performing all scans. (website, domain, IP, server)",  "Pentesting", AdvancedScanner,        {"target":   {"required": True, "nargs": 1, "help": "Service target: <URL> / <domain> / <IP[:port]> / <localhost[:port]>"},                                                                                                                                                                                                                                                                                                                                                                                                                                                                             "output": {"action": "store_true", "help": "Creating additional JSON output."},  "http-timeout": {"type": float, "help": "Set the maximum HTTP timeout in seconds: <timeout>"},             "socket-timeout":   {"type": float, "help": "Set the maximum socket timeout in seconds: <timeout>"},   "http-proxy": {"nargs": 1, "help": "Set an HTTP proxy: <proxy:port>"},            "socket-proxy": {"nargs": 1, "help": "Set a socket proxy: <proxy:port>"},   "useragent": {"nargs": 1, "help": "Set a user-agent: random / <useragent>"},               "cookie": {"nargs": 1, "help": "Set a cookie: <cookie>"}}),
        2     : ("Vulnerability Scanner",    "Scan all vulnerabilities of a website.",                                 "Pentesting", VulnerabilityScanner,   {"target":   {"required": True, "nargs": 1, "help": "Website target: <URL> / <domain> / <IP:port> / <localhost:port>"},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 "output": {"action": "store_true", "help": "Creating additional JSON output."},  "http-timeout": {"type": float, "help": "Set the maximum HTTP timeout in seconds: <timeout>"},                                                                                                                    "http-proxy": {"nargs": 1, "help": "Set an HTTP proxy: <proxy:port>"},                                                                                        "useragent": {"nargs": 1, "help": "Set a user-agent: random / <useragent>"},               "cookie": {"nargs": 1, "help": "Set a cookie: <cookie>"}}),
        3     : ("Port Scanner",             "Scan the ports of an IP.",                                               "Pentesting", PortScanner,            {"target":   {"required": True, "nargs": 1, "help": "IP target: <IP>"},                                                     "mode": {"required": True, "nargs": 1, "type": lambda x: x.lower(), "choices": ["single", "multiple", "range", "default", "all"], "help": "Scan mode: single / multiple / range / default / all"}, "port": {"nargs": "+", "help": "Port(s): single: <port> / multiple: <port>,<port> / range: <port>-<port>"}, "protocol-scan": {"nargs": 1, "type": lambda x: x.upper(), "choices": ["TCP", "UDP", "TCP,UDP", "UDP,TCP"], "help": "Protocol(s): TCP / UDP / TCP,UDP"},     "output": {"action": "store_true", "help": "Creating additional JSON output."},                                                                                                             "socket-timeout":   {"type": float, "help": "Set the maximum socket timeout in seconds: <timeout>"},                                                                                     "socket-proxy": {"nargs": 1, "help": "Set a socket proxy: <proxy:port>"}}),
        4     : ("URL Discovery Crawler",    "Scan all urls of a website.",                                            "Pentesting", UrlDiscoveryCrawler,    {"target":   {"required": True, "nargs": 1, "help": "Website target: <URL> / <domain> / <IP:port> / <localhost:port>"},     "mode": {"required": True, "nargs": 1, "type": lambda x: x.lower(), "choices": ["onlypage", "allwebsite"], "help": "Scan mode: onlypage / allwebsite"},                                                                                                                                                                                                                                                                                                                     "output": {"action": "store_true", "help": "Creating additional JSON output."},  "http-timeout": {"type": float, "help": "Set the maximum HTTP timeout in seconds: <timeout>"},                                                                                                                    "http-proxy": {"nargs": 1, "help": "Set an HTTP proxy: <proxy:port>"},                                                                                        "useragent": {"nargs": 1, "help": "Set a user-agent: random / <useragent>"},               "cookie": {"nargs": 1, "help": "Set a cookie: <cookie>"}}),
        5     : ("IP Pinger",                "Continuously ping an IP.",                                               "Pentesting", IpPinger,               {"target":   {"required": True, "nargs": 1, "help": "IP target: <IP>"},                                                     "mode": {"required": True, "nargs": 1, "type": lambda x: x.upper(), "choices": ["ICMP", "TCP"], "help": "Ping mode: ICMP / TCP"}, "bytes": {"nargs": "+", "help": "Set the number of bytes for an ICMP ping: <bytes>"}, "port": {"nargs": "+", "help": "Set the port for a TCP ping: <port>"}, "interval": {"type": float, "help": "Set the interval between each ping in seconds: <interval>"},                                                                                                                                                                                                                                                                        "socket-timeout":   {"type": float, "help": "Set the maximum socket timeout in seconds: <timeout>"},                                                                                     "socket-proxy": {"nargs": 1, "help": "Set a socket proxy: <proxy:port>"}}),
        6     : ("Host Discovery",           "Determines which hosts are online.",                                     "Pentesting", HostDiscovery,          {"target":   {"required": True, "nargs": 1, "help": "CIDR target: <IP>/<CIDR prefix>"},                                     "port": {"nargs": "+", "help": "Set the port for a TCP ping: <port>"},                                                                                                                                                                                                                                                                                                                                                                                                      "output": {"action": "store_true", "help": "Creating additional JSON output."},                                                                                                             "tcp-icmp-timeout": {"type": float, "help": "Set the maximum TCP/ICMP timeout in seconds: <timeout>"},                                                                                   "socket-proxy": {"nargs": 1, "help": "Set a socket proxy: <proxy:port>"}}),
        7     : ("Dorking Query Engine",     "Query builder for Google, Bing and DuckDuckGo with advanced operators.", "Osint",      DorkingQueryEngine,     {                                                                                                                           "engine": {"required": True, "nargs": 1, "type": lambda x: x.lower(), "choices": ["google", "bing", "duckduckgo"], "help": "Search engine: google / bing / duckduckgo"}}),
        8     : ("Wallet Tracker",           "Track a crypto wallet's transactions with APIs.",                        "Osint",      WalletTracker,          {"address":  {"required": True, "nargs": 1, "help": "Wallet target address: <address>"},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                "output": {"action": "store_true", "help": "Creating additional JSON output."},  "http-timeout": {"type": float, "help": "Set the maximum HTTP timeout for the API in seconds: <timeout>"},                                                                                                        "http-proxy": {"nargs": 1, "help": "Set an HTTP proxy for the API: <proxy:port>"},                                                                            "useragent": {"nargs": 1, "help": "Set a user-agent for the API: random / <useragent>"}}),
        9     : ("Username Tracker",         "Track a username across multiple platforms.",                            "Osint",      UsernameTracker,        {"target":   {"required": True, "nargs": 1, "help": "The target username: <username>"},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 "output": {"action": "store_true", "help": "Creating additional JSON output."},  "http-timeout": {"type": float, "help": "Set the maximum HTTP timeout in seconds: <timeout>"},                                                                                                                    "http-proxy": {"nargs": 1, "help": "Set an HTTP proxy: <proxy:port>"},                                                                                        "useragent": {"nargs": 1, "help": "Set a user-agent: random / <useragent>"}}),
        10    : ("Email Tracker",            "track an email registered on several platforms.",                        "Osint",      EmailTracker,           {"email":    {"required": True, "nargs": 1, "help": "Email target: <email>"},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           "output": {"action": "store_true", "help": "Creating additional JSON output."},  "http-timeout": {"type": float, "help": "Set the maximum HTTP timeout in seconds: <timeout>"},                                                                                                                    "http-proxy": {"nargs": 1, "help": "Set an HTTP proxy: <proxy:port>"},                                                                                        "useragent": {"nargs": 1, "help": "Set a user-agent: random / <useragent>"}}),
        11    : ("Email Lookup",             "Retrieve public data from an email.",                                    "Osint",      EmailLookup,            {"email":    {"required": True, "nargs": 1, "help": "Email target: <email>"},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           "output": {"action": "store_true", "help": "Creating additional JSON output."},                                                                                                             "socket-timeout":   {"type": float, "help": "Set the maximum socket timeout in seconds: <timeout>"},                                                                                     "socket-proxy": {"nargs": 1, "help": "Set a socket proxy: <proxy:port>"}}),
        12    : ("Ip Lookup",               f"Fetch public IP data using the \"{api_ip_lookup}\" API.",                "Osint",      IpLookup,               {"ip":       {"required": True, "nargs": 1, "help": "IP target: <IP>"},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 "output": {"action": "store_true", "help": "Creating additional JSON output."},  "http-timeout": {"type": float, "help": "Set the maximum HTTP timeout for the API in seconds: <timeout>"},                                                                                                        "http-proxy": {"nargs": 1, "help": "Set an HTTP proxy for the API: <proxy:port>"},                                                                            "useragent": {"nargs": 1, "help": "Set a user-agent for the API: random / <useragent>"}}),
        13    : ("Phone Number Lookup",      "Retrieve public data from a phone number.",                              "Osint",      PhoneNumerLookup,       {"phone":    {"required": True, "nargs": 1, "help": "Phone number target: <number>"},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   "output": {"action": "store_true", "help": "Creating additional JSON output."}}),
        14    : ("Instagram Profile Lookup", "Retrieve public data from an instagram username.",                       "Osint",      InstagramProfileLookup, {"target":   {"required": True, "nargs": 1, "help": "Username target: <username>"},                                         "sessionid": {"required": True, "nargs": 1, "help": "Your instagram id session: <sessionid>"},                                                                                                                                                                                                                                                                                                                                                                              "output": {"action": "store_true", "help": "Creating additional JSON output."},                                                                                                                                                                                                                    "http-proxy": {"nargs": 1, "help": "Set an HTTP proxy: <proxy:port>"},                                                                                        "useragent": {"nargs": 1, "help": "Set a user-agent: random / <useragent>"}}),
        15    : ("File Metadata Scanner",    "Scan all file metadata.",                                                "Utilities",  FileMetadataScanner,    {"path":     {"required": True, "nargs": 1, "help": "The file path: <path>"},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           "output": {"action": "store_true", "help": "Creating additional JSON output."}}),
        16    : ("File Metadata Deleter",    "Remove all file metadata.",                                              "Utilities",  FileMetadataDeleter,    {"path":     {"required": True, "nargs": 1, "help": "The file path: <path>"}}),
        17    : ("Website Cloner",           "Clone the entire web page.",                                             "Utilities",  WebsiteCloner,          {"target":   {"required": True, "nargs": 1, "help": "Website target: <URL> / <domain> / <IP:port> / <localhost:port>"},                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  "http-timeout": {"type": float, "help": "Set the maximum HTTP timeout in seconds: <timeout>"},                                                                                                                    "http-proxy": {"nargs": 1, "help": "Set an HTTP proxy: <proxy:port>"},                                                                                        "useragent": {"nargs": 1, "help": "Set a user-agent: random / <useragent>"},                "cookie": {"nargs": 1, "help": "Set a cookie: <cookie>"}}),
    }

    options_hidden_list = {
    #   Number   Name               Description                                          Category  Function        Argument
        100   : ("Help",            "Shows all tools options.",                          "Tools" , Help,           {}),
        101   : ("Version",         "Displays the version and information of the tool.", "Tools" , Version,        {}),
        102   : ("Settings Update", "Update the tools settings.",                        "Tools" , SettingsUpdate, {"mode": {"required": True, "nargs": "?", "choices": ["decorated", "interface"], "help": "Mode: decorated / interface"}, "status": {"required": True, "nargs": "?", "choices": ["enable", "disable"], "help": "Status: enable / disable"}}),
    }

    options_list = InjectPlugins(options_list)
    option_names = {}
    option_categories = {}
    for i, (name, description, category, function, argument) in options_list.items():
        option_names[i] = f"{BEFORE}{i:02d}{AFTER}{white} {name.ljust(25)[:25]}"
        option_categories.setdefault(category, []).append(i)
    return option_names, option_categories, options_list, options_hidden_list

def HandleCli(options_list, options_hidden_list):
    parser = RedTigerArgumentParser(description=f"{tool_name} {tool_version}", add_help=False, allow_abbrev=False)

    cli_map = {}
    tool_args = {}

    merged_options = options_list.copy()
    if options_hidden_list: merged_options.update(options_hidden_list)

    for _, option in merged_options.items():
        name, description, category, function, arguments = option

        if function is None: continue

        arg_name = name.lower().replace(" ", "-")
        arg_key = arg_name.replace("-", "_")
 
        if function == Help:
            parser.add_argument(f"--{arg_name}", f"-{''.join([p[0] for p in arg_name.split('-') if p])}", action="store_true")
            cli_map[arg_key] = lambda **_: Help(options_list, options_hidden_list)
            cli_map["h"] = lambda **_: Help(options_list, options_hidden_list)
            continue

        parser.add_argument(f"--{arg_name}", f"-{''.join([p[0] for p in arg_name.split('-') if p])}", action="store_true")
        cli_map[arg_key] = function
        tool_args[arg_key] = arguments

    base_args, remaining_argv = parser.parse_known_args()
    base_dict = vars(base_args)

    selected_key = None
    selected_func = None

    for key, func in cli_map.items():
        if base_dict.get(key):
            selected_key = key
            selected_func = func
            break

    if not selected_func: return

    parser = RedTigerArgumentParser(description=f"{tool_name} {tool_version}", add_help=False, allow_abbrev=False)
    parser.add_argument(f"--{selected_key.replace('_','-')}", action="store_true")
    arguments = tool_args.get(selected_key, {})

    for arg, params in arguments.items():
        valid_params = {k: v for k, v in params.items() if k in ("nargs", "choices", "help", "default", "type", "action")}
        parser.add_argument(f"--{arg}", "-" + (lambda x: x[0].lower() if len(x) == 1 else "".join(c.upper() for c in x))([p[0] for p in arg.split("-") if p]), dest=arg.replace("-", "_"), **valid_params)

    args = parser.parse_args(remaining_argv)
    args_dict = vars(args)

    kwargs = {}
    for k in arguments.keys():
        py_key = k.replace("-", "_")
        v = args_dict.get(py_key)
        if isinstance(v, list) and len(v) == 1:
            v = v[0]
        kwargs[py_key] = v

    print(MainColor(f"{banner_redtiger}\n"))
    selected_func(**kwargs)
    sys.exit()

def BuildMenu(option_names, option_categories, options_list):
    categories = []
    max_lines       = 0
    col_width       = 45
    empty_col_width = 30 

    for category, indexes in option_categories.items():
        lines = [option_names[i] for i in indexes if options_list[i][3] is not None]
        if lines:
            categories.append((category, lines))
            max_lines = max(max_lines, len(lines))

    output  = f"  {BEFORE}H{AFTER + white} Help\n"
    output += f"  {BEFORE}V{AFTER + white} Version\n"
    output += f"  {BEFORE}S{AFTER + white} Settings\n\n"
    title_line = "  "

    for category, _ in categories: title_line += f"{BEFORE + category + AFTER:<{col_width}}"
    if not any(category == "Plugins" for category, _ in categories): title_line += f"{BEFORE + 'Plugins' + AFTER:<{col_width}}"
    output += title_line.rstrip() + "\n\n"

    for i in range(max_lines):
        line = "  "
        for _, lines in categories:
            if i < len(lines): line += f"{lines[i]:<{col_width}}"
            else: line += " " * empty_col_width
        output += line.rstrip() + "\n"

    return output
    
def Menu():
    option_names, option_categories, options_list, options_hidden_list = Options()

    if has_cli_args: HandleCli(options_list, options_hidden_list)
    else:
        if version_interface:
            while True:
                Title("Tools")
                Clear()
                menu = BuildMenu(option_names, option_categories, options_list)
                Slow(MainColor(f"{banner_redtiger}\n"))
                Slow(menu)
                choice = input(MainColor(f" ┌──({white}{os_username}@redtiger)─{red}[{white}") + path_folder_tool + MainColor(f"]\n └─{white}$ {reset}")).strip().lower()
                try:
                    if choice in ("h", "help"): 
                        Help(options_list, options_hidden_list)
                        continue
                    elif choice in ("v", "version"): 
                        print()
                        Version()
                        continue
                    elif choice in ("s", "settings"): 
                        SettingsUpdate()
                        continue
                    name, description, category, function, argument = options_list[int(choice)]
                    if int(choice) not in options_list or function is None:
                        ErrorChoiceStart()
                        continue
                    else:
                        try:
                            print() 
                            function()
                        except Exception as e: ErrorUnknown(f"Error {name}: {white + str(e)}")
                except (ValueError, IndexError): 
                    ErrorChoiceStart()
                    continue
        else:
            print(MainColor(f"{banner_redtiger}\n"))
            Help(options_list, options_hidden_list)

CheckUpdate()
Menu()