# Copyright (c) RedTiger by Loxy0devlp
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from Config.Utils import *

def Scan(session, target, http_timeout):
    platform_found = []

    for name, data in data_username_tracker_plateforms.items():
        try:
            url             = data["url"].replace("%USERNAME%", target)
            method          = data["method"]
            verification    = data["verification"]
            page_except     = [key.replace("%USERNAME%", target) for key in (data.get("except") or [])]
            found           = False

            if method == "get": response = session.get(url, timeout=http_timeout)
            if response.status_code == 200:
                soup         = bs4.BeautifulSoup(response.text, 'html.parser')
                page_content = re.sub(r'<[^>]*>', '', response.text.lower().replace(url, "").replace(f"/{target}", ""))
                page_text    = soup.get_text().lower().replace(url, "")
                page_title   = soup.title.string.lower() if soup.title and soup.title.string else ""

                if "status" in verification:
                    found = True
                    if page_except:
                        for page_content_except in page_except:
                            if page_content_except.lower() in page_content or page_content_except.lower() in page_text or page_content_except.lower() in page_title: 
                                found = False

                elif "username" in verification:
                    if page_except:
                        for page_content_except in page_except:
                            page_content = page_content.replace(page_content_except.lower(), '')
                            page_text    = page_text.replace(page_content_except.lower(), '')
                            page_title   = page_title.replace(page_content_except.lower(), '')
                    found = target in page_title or target in page_content or target in page_text
                
                elif "keyword" in verification:
                    found = False
                    if page_except:
                        for page_content_except in page_except:
                            if page_content_except.lower() in page_content or page_content_except.lower() in page_text or page_content_except.lower() in page_title: 
                                found = True

                if found:
                    platform_found.append({name: url})
                    Add(f"{name}: {green}{url}")
                else:
                    Error(f"{name}: {white}Not found")
            else:
                Error(f"{name}: {white}Not found")

        except requests.exceptions.ReadTimeout:      Error(f"{name}: {white}Error: Timeout")
        except requests.exceptions.RequestException: Error(f"{name}: {white}Error: Connection failed")
        except ConnectionError:                      Error(f"{name}: {white}Error: Connection failed")
        except Exception as e:                       Error(f"{name}: {white}Error: {e}")

        state["completed"] += 1

    return platform_found

def UsernameTracker(target=None, http_timeout=None, http_proxy=None, useragent=None, output=None):
    Title("Username Tracker")

    if not target: target = Input("Target [-t] -> ")

    if not has_cli_args: 
        http_timeout = Input(f"Max HTTP timeout [-HT] (default: {str(default_http_timeout)}) -> ")
        http_proxy   = Input(f"HTTP proxy [-HP] (default: {str(default_http_proxy)}) -> ")
        useragent    = Input(f"User-Agent [-u] (for random: random, default: {str(default_useragent)}) -> ")

    if not http_proxy: http_proxy = default_http_proxy
    if not useragent : useragent  = default_useragent

    try:
        if not http_timeout: http_timeout = default_http_timeout
        else: http_timeout = float(http_timeout)
        Info(f"Max HTTP timeout: {white}{str(http_timeout)}s")
    except (ValueError, TypeError): ErrorTimeout()

    session, proxies, cookie, useragent = EnableHttpProxyAndUserAgentAndCookie(http_proxy=http_proxy, useragent=useragent, http_timeout=http_timeout, enable_cookie=False)

    Wait("Scanning..")
    
    global state
    platform_number_total = len(data_username_tracker_plateforms)
    state = {"stop": False, "completed": 0, "completed_total": platform_number_total}
    StartThread(StatsPressed, state, time_start=time.time())

    platform_found = Scan(session, target, http_timeout)
    platform_number_found = len(platform_found)
    state["stop"] = True
    
    Info(f"Total Found: {white}{platform_number_found}/{platform_number_total}")

    json_data = {
        "Parameters": {
            "Target": target,
            "HTTP timeout": http_timeout if http_timeout else None,
            "HTTP proxy": http_proxy if http_proxy else None,
            "User-agent": useragent if useragent else None,
        },
        "Found": platform_found,
        "Not found": platform_number_total - platform_number_found
    }
    
    if output in (True, None): SaveJsonToFile(json_data, f"Result_UsernameTracker_{target}", json_output=output)
    Continue()
    Reset()