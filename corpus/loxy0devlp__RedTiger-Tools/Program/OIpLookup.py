# Copyright (c) RedTiger by Loxy0devlp
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from Config.Utils import *
from Program.Utils.NetworkScanningUtils import *

def IpLookup(ip=None, http_timeout=None, http_proxy=None, useragent=None, output=None):
    Title("Ip Lookup")

    Info(f"This option uses the API of \"{api_ip_lookup}\"")

    if not ip: ip = Input("IP [-i] -> ")
    detect_target = DetectTarget(ip)

    if not detect_target in ["ip"]: ErrorIp()
    elif any(bad in ip for bad in blacklists): ErrorTarget()

    if not has_cli_args: 
        http_timeout = Input(f"Max HTTP timeout for the API [-HT] (default: {str(default_http_timeout)}) -> ")
        http_proxy   = Input(f"HTTP proxy for the API [-HP] (default: {str(default_http_proxy)}) -> ")
        useragent    = Input(f"User-Agent for the API [-u] (for random: random, default: {str(default_useragent)}) -> ")
    
    if not http_proxy: http_proxy = default_http_proxy
    if not useragent : useragent  = default_useragent

    try:
        if not http_timeout: http_timeout = default_http_timeout
        else: http_timeout = float(http_timeout)
        Info(f"Max HTTP timeout for the API: {white}{str(http_timeout)}s")
    except (ValueError, TypeError): ErrorTimeout()

    session, proxies, cookie, useragent = EnableHttpProxyAndUserAgentAndCookie(http_proxy=http_proxy, useragent=useragent, http_timeout=http_timeout, enable_cookie=False)

    Wait("Waiting for API response..")

    vars, json_format = IpGetLookup(ip, session, http_timeout, log=True)

    json_data = {
        "Parameters": {
            "IP": ip,
            "API": api_ip_lookup,
            "HTTP timeout": http_timeout if http_timeout else None,
            "HTTP proxy": http_proxy if http_proxy else None,
            "User-agent": useragent if useragent else None,
        },
        "Informations": json.loads(json_format)
    }

    if output in (True, None): SaveJsonToFile(json_data, f"Result_IpLookup_{ip}", json_output=output)
    Continue()
    Reset()