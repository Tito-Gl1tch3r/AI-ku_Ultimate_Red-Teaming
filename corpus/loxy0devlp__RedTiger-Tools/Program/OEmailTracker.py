# Copyright (c) RedTiger by Loxy0devlp
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from Config.Utils import *
from Program.Utils.NetworkScanningUtils import *

def Twitter(email, session, http_timeout):
    try:
        response = session.get(url="https://api.twitter.com/i/users/email_available.json", params={"email": email}, timeout=http_timeout)
        if response.status_code == 200: return response.json()["taken"]
        return False
    except Exception as e: return f"Error: {white}{e}"
    
def Spotify(email, session, http_timeout):  
    headers = {
        "Accept": "application/json, text/plain, */*", 
        "Accept-Language": "en-US,en;q=0.5", 
        "DNT": "1", "Connection": 
        "keep-alive",
    }

    params = {
        "validate": "1", 
        "email": email
    }

    try:
        response = session.get("https://spclient.wg.spotify.com/signup/public/v1/account", headers=headers, params=params, timeout=http_timeout)
        if response.status_code == 200: return response.json()["status"] == 20
        return False
    except Exception as e: return f"Error: {white}{e}"

def Deezer(email, session, http_timeout):
    try:
        response = session.post("https://www.deezer.com/ajax/gw-light.php?method=deezer.getUserData&input=3&api_version=1.0&api_token=&cid=", timeout=http_timeout)
        token    = response.json()["results"]["checkForm"]

        params = {
            "method": "deezer.emailCheck",
            "input": 3,
            "api_version": 1.0,
            "api_token": token,
        }

        data = "{\"EMAIL\":\"" + email + "\"}"

        response = session.post(f"https://www.deezer.com/ajax/gw-light.php", params=params, data=data, timeout=http_timeout)
        if response.json()["results"]["availability"] == False: return True
        return False
    except Exception as e: return f"Error: {white}{e}"

def Chess(email, session, http_timeout):
    try:
        response = session.post(f"https://www.chess.com/callback/email/available?email={email}", timeout=http_timeout)
        if response.json()["isEmailAvailable"] == False: return True
        return False
    except Exception as e: return f"Error: {white}{e}"

def Duolingo(email, session, http_timeout):
    params = {
        "email": email
    }
    
    try:
        response = session.get(f"https://www.duolingo.com/2017-06-30/users", params=params, timeout=http_timeout)
        if """{"users":[]}""" in response.text: return False
        return True
    except Exception as e: return f"Error: {white}{e}"

def Archive(email, session, http_timeout):
    headers = {
        "Accept": "*/*", 
        "Accept-Language": "en,en-US;q=0.5", 
        "Content-Type": "multipart/form-data; boundary=---------------------------", 
        "Origin": "https://archive.org", 
        "Connection": "keep-alive", 
        "Referer": "https://archive.org/account/signup",
        "Sec-GPC": "1",
        "TE": "Trailers",
    }

    data = "-----------------------------\r\nContent-Disposition: form-data; name=\"input_name\"\r\n\r\nusername\r\n-----------------------------\r\nContent-Disposition: form-data; name=\"input_value\"\r\n\r\n" + email + "\r\n-----------------------------\r\nContent-Disposition: form-data; name=\"input_validator\"\r\n\r\ntrue\r\n-----------------------------\r\nContent-Disposition: form-data; name=\"submit_by_js\"\r\n\r\ntrue\r\n-------------------------------\r\n"
    
    try:
        response = session.post("https://archive.org/account/signup", headers=headers, data=data, timeout=http_timeout)
        if response.status_code == 200: return "is already taken" in response.text
        return False
    except Exception as e: return f"Error: {white}{e}"

def Patreon(email, session, http_timeout):
    headers = {
        "Accept": "*/*",
        "Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.plurk.com",
        "DNT": "1",
        "Connection": "keep-alive",
    }

    data = {
        "email": email
    }

    try:
        response = session.post("https://www.plurk.com/Users/isEmailFound", headers=headers, data=data, timeout=http_timeout)
        if response.status_code == 200: return "True" in response.text
        return False
    except Exception as e: return f"Error: {white}{e}"

def Firefox(email, session, http_timeout):
    data = {
        "email": email
    }

    try:
        response = session.post("https://api.accounts.firefox.com/v1/account/status", data=data, timeout=http_timeout)
        if response.status_code == 200: return "false" not in response.text
        return False
    except Exception as e: return f"Error: {white}{e}"

def Adobe(email, session, http_timeout):
    data = {
        "username": email,
        "usernameType": "EMAIL"
    }

    headers = {
        "x-ims-clientid": "homepage_milo",
        "content-type": "application/json"
    }

    try:
        response = session.post("https://auth.services.adobe.com/signin/v2/users/accounts", headers=headers, json=data, timeout=http_timeout)
        if response.json():
            if response.json()[0]["authenticationMethods"]: return True
        return False
    except Exception as e: return f"Error: {white}{e}"

def Xvideo(email, session, http_timeout):
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Connection": "keep-alive",
        "Referer": "https://www.xvideos.com/",
    }

    params  = {
        "email": email
    }

    try:
        response = session.get("https://www.xvideos.com/account/checkemail", headers=headers, params=params, timeout=http_timeout)
        if response.status_code == 200:
            try:
                if response.json()["message"] == "This email is already in use or its owner has excluded it from our website.": return True
                elif response.json()["message"] == "Invalid email address.": return False
            except: pass    
            if response.json()["result"]   == "false": return True
            elif response.json()["code"]   == 1:       return True
            elif response.json()["result"] == "true":  return False
            elif response.json()["code"]   == 0:       return False  
        return False
    except Exception as e: return f"Error: {white}{e}"

def Xnxx(email, session, http_timeout):
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-en",
        "Host": "www.xnxx.com",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive"
    }
    
    try:
        cookie = session.get("https://www.xnxx.com", headers=headers, timeout=http_timeout)
        if cookie.status_code != 200: return f"Error: {white}Unable to retrieve the cookie ({cookie.status_code})"

        headers["Referer"]          = "https://www.xnxx.com/video-holehe/palenath_fucks_xnxx_with_holehe"
        headers["X-Requested-With"] = "XMLHttpRequest"
        email    = email.replace("@", "%40")
        response = session.get(f"https://www.xnxx.com/account/checkemail?email={email}", headers=headers, cookies=cookie.cookies, timeout=http_timeout)
        
        if response.status_code == 200:
            try:
                if response.json()["message"] == "This email is already in use or its owner has excluded it from our website.": return True
                elif response.json()["message"] == "Invalid email address.": return False
            except: pass    
            if response.json()["result"]   == "false": return True
            elif response.json()["code"]   == 1:       return True
            elif response.json()["result"] == "true":  return False
            elif response.json()["code"]   == 0:       return False  
        return False
    except Exception as e: return f"Error: {white}{e}"

platforms = {
    "X (Twitter)"       : Twitter,
    "Spotify"           : Spotify,
    "Deezer"            : Deezer,
    "Chess"             : Chess,
    "Duolingo"          : Duolingo,
    "Archive"           : Archive,
    "Patreon"           : Patreon,
    "Firefox (Mozilla)" : Firefox,
    "Adobe"             : Adobe,
    "Xvideo"            : Xvideo,
    "Xnxx"              : Xnxx
}

def Scan(email, session, http_timeout):
    platform_found = []

    for name, func in platforms.items():
        result = func(email, session, http_timeout)
        if result == True: 
            Add(f"{name}: {green}{result}")
            platform_found.append(name)
        else: Error(f"{name}: {white}{result}")
        state["completed"] += 1
    
    return platform_found

def EmailTracker(email=None, http_timeout=None, http_proxy=None, useragent=None, output=None):
    Title("Email Tracker")

    if not email: email = Input("Email [-e] -> ")
    if not "@" in email: ErrorEmail()

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
    platform_number_total = len(platforms)
    state = {"stop": False, "completed": 0, "completed_total": platform_number_total}
    StartThread(StatsPressed, state, time_start=time.time())

    platform_found = Scan(email, session, http_timeout)
    platform_number_found = len(platform_found)
    state["stop"] = True
    
    Info(f"Total Found: {white}{platform_number_found}/{platform_number_total}")

    json_data = {
        "Parameters": {
            "Email": email,
            "HTTP timeout": http_timeout if http_timeout else None,
            "HTTP proxy": http_proxy if http_proxy else None,
            "User-agent": useragent if useragent else None,
        },
        "Found": platform_found,
        "Not found": platform_number_total - platform_number_found
    }
    
    if output in (True, None): SaveJsonToFile(json_data, f"Result_EmailTracker_{email}", json_output=output)
    Continue()
    Reset()