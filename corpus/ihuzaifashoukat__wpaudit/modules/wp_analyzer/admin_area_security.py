# Module for WordPress Admin Area Security Checks
import requests
import re # For plugin footprint detection
from urllib.parse import urljoin
from .utils import make_request # Assuming a utility for requests exists
import copy # Added for deepcopy

# Common alternative admin paths (non-exhaustive)
COMMON_ALT_ADMIN_PATHS = [
    "login", "admin", "dashboard", "wp-admin-hidden", "my-admin", "secret-admin",
    "control-panel", "cpanel", "admin-login", "member-login", "site-admin",
    "backend", "manage", "webadmin", "admin123", "adm", "portal", "secure"
]

# Footprints for admin protection plugins
ADMIN_PLUGIN_FOOTPRINTS = {
    "WPS Hide Login": [
        re.compile(r"<!-- WPS Hide Login", re.IGNORECASE),
        re.compile(r"/wp-content/plugins/wps-hide-login/", re.IGNORECASE)
    ],
    "Protect Your Admin": [ # Example, ensure real footprints if this plugin is common
        re.compile(r"Protect Your Admin - Active", re.IGNORECASE)
    ],
    "Limit Login Attempts Reloaded": [
        re.compile(r"limit-login-attempts-reloaded", re.IGNORECASE),
        re.compile(r"llar_protect_script", re.IGNORECASE)
    ],
    "Wordfence Security": [
        re.compile(r"/wp-content/plugins/wordfence/", re.IGNORECASE),
        re.compile(r"<!-- Wordfence WAF -->", re.IGNORECASE),
        re.compile(r"wordfence_syncAttackData", re.IGNORECASE)
    ],
    "iThemes Security (Better WP Security)": [
        re.compile(r"/wp-content/plugins/better-wp-security/", re.IGNORECASE),
        re.compile(r"<!-- iThemes Security -->", re.IGNORECASE),
        re.compile(r"itsec_wp_admin_restriction_settings", re.IGNORECASE) # Option name
    ],
    "Sucuri Security": [
        re.compile(r"/wp-content/plugins/sucuri-scanner/", re.IGNORECASE),
        re.compile(r"<!-- Sucuri WordPress Security -->", re.IGNORECASE),
        re.compile(r"sucuri_firewall_settings", re.IGNORECASE) # Option name
    ],
    "All In One WP Security & Firewall": [
        re.compile(r"/wp-content/plugins/all-in-one-wp-security-and-firewall/", re.IGNORECASE),
        re.compile(r"AIOWPS", re.IGNORECASE), # Common prefix or class
        re.compile(r"aiowps_login_security_options", re.IGNORECASE) # Option name
    ],
    "Cerber Security, Antispam & Malware Scan": [
        re.compile(r"/wp-content/plugins/wp-cerber/", re.IGNORECASE),
        re.compile(r"wpcerber_login_form", re.IGNORECASE) # Function or hook
    ]
    # Add more plugins and their footprints
}

# Footprints for CAPTCHA services
CAPTCHA_FOOTPRINTS = {
    "Google reCAPTCHA": [
        re.compile(r"google.com/recaptcha/api.js", re.IGNORECASE),
        re.compile(r"g-recaptcha", re.IGNORECASE),
        re.compile(r"class=\"grecaptcha-badge\"", re.IGNORECASE)
    ],
    "hCaptcha": [
        re.compile(r"hcaptcha.com/1/api.js", re.IGNORECASE),
        re.compile(r"h-captcha", re.IGNORECASE)
    ],
    "Cloudflare Turnstile": [
        re.compile(r"challenges.cloudflare.com/turnstile/v0/api.js", re.IGNORECASE),
        re.compile(r"cf-turnstile", re.IGNORECASE)
    ],
    "Really Simple CAPTCHA": [ # Common WP Plugin
        re.compile(r"/wp-content/plugins/really-simple-captcha/", re.IGNORECASE),
        re.compile(r"class=\"wpcf7-captchar\"", re.IGNORECASE) # Often used with Contact Form 7
    ]
}

# Footprints/Keywords for Two-Factor Authentication (2FA)
TWO_FACTOR_AUTH_FOOTPRINTS = {
    "Generic 2FA Keywords": [
        re.compile(r"two-factor", re.IGNORECASE),
        re.compile(r"authentication code", re.IGNORECASE),
        re.compile(r"verification code", re.IGNORECASE),
        re.compile(r"one-time password", re.IGNORECASE),
        re.compile(r"2fa token", re.IGNORECASE)
    ],
    "Wordfence Login Security (2FA)": [ # Wordfence also provides 2FA
        re.compile(r"wordfence-2fa", re.IGNORECASE),
        re.compile(r"id=\"wf-2fa-code\"", re.IGNORECASE)
    ],
    "Google Authenticator (Plugin)": [ # Common plugin name
        re.compile(r"google-authenticator", re.IGNORECASE), # Plugin slug or class
        re.compile(r"id=\"ga_code\"", re.IGNORECASE) # Example ID for code input
    ],
    "iThemes Security (2FA)": [ # iThemes also provides 2FA
        re.compile(r"it-security-two-factor", re.IGNORECASE),
        re.compile(r"itsec_two_factor_options", re.IGNORECASE), # Option name
        re.compile(r"id=\"itsec-otp-code\"", re.IGNORECASE)
    ],
    "Two Factor Authentication (by miniOrange)": [
        re.compile(r"miniorange-2-factor-authentication", re.IGNORECASE) # Plugin slug
    ]
}


def _check_path_accessibility(url, config, path_description):
    """Helper to check accessibility and HTTP Auth for a given path."""
    is_accessible = None
    http_auth = False
    status_code = None
    content_snippet = ""
    redirect_location = None
    headers = {}

    print(f"      Checking {path_description}: {url}")
    try:
        response = make_request(url, config, method="GET", allow_redirects=False, timeout=7)
        if response:
            status_code = response.status_code
            content_snippet = response.text[:10000] if response.text else "" # Increased snippet size for more comprehensive footprint analysis
            redirect_location = response.headers.get('Location')
            headers = response.headers

            if status_code == 401:
                http_auth = True
                is_accessible = True # Path exists but is protected by HTTP Auth
                print(f"        [+] HTTP Authentication detected on {path_description}.")
            elif 200 <= status_code < 300:
                is_accessible = True
                print(f"        [+] {path_description} directly accessible (Status: {status_code}).")
            elif 300 <= status_code < 400 and redirect_location:
                is_accessible = True # Path exists, redirects
                print(f"        [+] {path_description} redirects to {redirect_location} (Status: {status_code}).")
            else: # 404, 403 (other than 401), 5xx etc.
                is_accessible = False
                print(f"        [-] {path_description} not accessible or blocked (Status: {status_code}).")
        else:
            print(f"        [-] Request failed for {path_description}.")
    except requests.exceptions.RequestException as e:
        print(f"        [-] Error checking {path_description} at {url}: {e}")
    
    return is_accessible, http_auth, status_code, content_snippet, redirect_location, headers


def analyze_admin_area_security(state, config, target_url):
    """
    Enhanced checks for admin area security: standard paths, HTTP Auth,
    common alternative paths, footprints of protection plugins, CAPTCHA, and 2FA.
    """
    module_key = "wp_analyzer"
    findings_key = "admin_area_security"

    _DEFAULT_ADMIN_AREA_SECURITY_FINDINGS = {
        "status": "Not Run",
        "details": "Checking admin area security aspects...",
        "standard_login_status": {"accessible": None, "http_auth": False, "status_code": None, "content_snippet": "", "redirect_url": None, "headers": {}},
        "standard_admin_dir_status": {"accessible": None, "http_auth": False, "status_code": None, "content_snippet": "", "redirect_url": None, "headers": {}},
        "alternative_admin_paths_found": [],
        "detected_protection_plugins": [],
        "detected_captcha_services": [],
        "detected_2fa_mechanisms": [],
        "htaccess_protection_wp_admin": "Unknown",
        "brute_force_protection_hint": "Unknown" # New field
    }

    all_wp_analyzer_findings_raw = state.get_module_findings(module_key, {})
    if not isinstance(all_wp_analyzer_findings_raw, dict):
        all_wp_analyzer_findings = {}
    else:
        all_wp_analyzer_findings = all_wp_analyzer_findings_raw
        
    existing_findings = all_wp_analyzer_findings.get(findings_key, {})

    findings = copy.deepcopy(_DEFAULT_ADMIN_AREA_SECURITY_FINDINGS)

    if isinstance(existing_findings, dict):
        for key, value in existing_findings.items():
            if key in findings:
                if isinstance(findings[key], dict) and isinstance(value, dict):
                    findings[key].update(value)
                elif isinstance(findings[key], list) and isinstance(value, list):
                    findings[key].extend(v for v in value if v not in findings[key])
                else:
                    findings[key] = value

    findings["status"] = "Running"
        
    all_wp_analyzer_findings[findings_key] = findings
    state.update_module_findings(module_key, all_wp_analyzer_findings)

    print("    [i] Analyzing Admin Area Security...")

    # 1. Check standard wp-login.php
    login_url = urljoin(target_url, 'wp-login.php')
    is_acc, http_auth, sc, content, redir, headers = _check_path_accessibility(login_url, config, "standard wp-login.php")
    findings["standard_login_status"] = {"accessible": is_acc, "http_auth": http_auth, "status_code": sc, "content_snippet": content, "redirect_url": redir, "headers": dict(headers)}
    login_page_content_for_plugins = content if is_acc else ""
    login_page_headers = headers if is_acc else {}

    # 2. Check standard wp-admin/
    admin_dir_url = urljoin(target_url, 'wp-admin/')
    is_acc_admin, http_auth_admin, sc_admin, content_admin, redir_admin, headers_admin = _check_path_accessibility(admin_dir_url, config, "standard wp-admin directory")
    findings["standard_admin_dir_status"] = {"accessible": is_acc_admin, "http_auth": http_auth_admin, "status_code": sc_admin, "content_snippet": content_admin, "redirect_url": redir_admin, "headers": dict(headers_admin)}
    
    if findings["standard_admin_dir_status"]["redirect_url"] and \
       'wp-login.php' in findings["standard_admin_dir_status"]["redirect_url"] and \
       findings["standard_login_status"]["accessible"]:
        print("        [i] wp-admin correctly redirects to wp-login.php.")

    # 3. Check for common alternative admin paths
    if findings["standard_login_status"]["accessible"] is False:
        print("    [i] Standard wp-login.php seems inaccessible or hidden, checking common alternative admin paths...")
        for alt_path in COMMON_ALT_ADMIN_PATHS:
            alt_url = urljoin(target_url, alt_path)
            if alt_url == target_url or alt_url == target_url + "/": 
                continue

            is_acc_alt, http_auth_alt, sc_alt, content_alt, redir_alt, headers_alt = _check_path_accessibility(alt_url, config, f"alternative path '{alt_path}'")
            if is_acc_alt:
                login_keywords = ["log in", "username", "password", "user name", "pass word", "forgot password", "sign in"]
                is_likely_login = any(kw in content_alt.lower() for kw in login_keywords) if content_alt else False
                
                path_info = {"path": alt_path, "url": alt_url, "status_code": sc_alt, "http_auth": http_auth_alt, "is_likely_login_page": is_likely_login, "redirect_url": redir_alt, "headers": dict(headers_alt)}
                findings["alternative_admin_paths_found"].append(path_info)
                print(f"        [+] Found potentially active alternative admin path: {alt_url} (Likely Login: {is_likely_login})")
                if not login_page_content_for_plugins and is_likely_login:
                    login_page_content_for_plugins = content_alt
                    login_page_headers = headers_alt # Use headers from this page too

    # Use content from the most relevant accessible login page for footprint analysis
    page_content_for_analysis = login_page_content_for_plugins
    relevant_headers = login_page_headers

    # If standard login failed but an alternative was found and seems like a login page, prioritize its content
    if not findings["standard_login_status"]["accessible"] and findings["alternative_admin_paths_found"]:
        for alt_path_info in findings["alternative_admin_paths_found"]:
            if alt_path_info["is_likely_login_page"]:
                # Re-fetch content if not already captured, or use from check
                # For simplicity, we assume _check_path_accessibility returned enough content
                # This part might need refinement if content_alt wasn't stored broadly
                # For now, we rely on login_page_content_for_plugins being updated correctly in step 3
                break # Use the first likely alternative login page's content

    if page_content_for_analysis:
        print("    [i] Analyzing login page content for plugin footprints, CAPTCHA, and 2FA...")
        # 4. Detect Admin Protection / Login Security Plugins
        for plugin_name, patterns in ADMIN_PLUGIN_FOOTPRINTS.items():
            for pattern in patterns:
                if pattern.search(page_content_for_analysis):
                    if plugin_name not in findings["detected_protection_plugins"]:
                        findings["detected_protection_plugins"].append(plugin_name)
                        print(f"        [+] Detected footprint for protection plugin: {plugin_name}")
                        break
        
        # 5. Detect CAPTCHA services
        for service_name, patterns in CAPTCHA_FOOTPRINTS.items():
            for pattern in patterns:
                if pattern.search(page_content_for_analysis):
                    if service_name not in findings["detected_captcha_services"]:
                        findings["detected_captcha_services"].append(service_name)
                        print(f"        [+] Detected footprint for CAPTCHA service: {service_name}")
                        break
        
        # 6. Detect 2FA mechanisms
        for mechanism_name, patterns in TWO_FACTOR_AUTH_FOOTPRINTS.items():
            for pattern in patterns:
                if pattern.search(page_content_for_analysis):
                    if mechanism_name not in findings["detected_2fa_mechanisms"]:
                        findings["detected_2fa_mechanisms"].append(mechanism_name)
                        print(f"        [+] Detected footprint for 2FA mechanism: {mechanism_name}")
                        break
    else:
        print("    [i] No accessible login page content to analyze for footprints.")

    # 7. Check for wp-admin/.htaccess (heuristic)
    htaccess_url = urljoin(target_url, 'wp-admin/.htaccess')
    print(f"    [i] Heuristically checking for wp-admin/.htaccess protection at {htaccess_url}")
    try:
        response_htaccess = make_request(htaccess_url, config, method="GET", timeout=5)
        if response_htaccess:
            if response_htaccess.status_code == 403:
                findings["htaccess_protection_wp_admin"] = "Potentially Protected (403 Forbidden)"
                print("        [+] Received 403 Forbidden for wp-admin/.htaccess, suggesting it might be present and access controlled.")
            elif response_htaccess.status_code == 404:
                findings["htaccess_protection_wp_admin"] = "Not Directly Accessible (404)"
                print("        [-] wp-admin/.htaccess not directly accessible (404). Could be absent or protected by server config.")
            else:
                findings["htaccess_protection_wp_admin"] = f"Unexpected Status ({response_htaccess.status_code})"
                print(f"        [?] Unexpected status {response_htaccess.status_code} for wp-admin/.htaccess.")
        else:
            findings["htaccess_protection_wp_admin"] = "Request Failed"
            print("        [-] Request failed for wp-admin/.htaccess check.")
    except requests.exceptions.RequestException as e:
        findings["htaccess_protection_wp_admin"] = "Error During Check"
        print(f"        [-] Error checking {htaccess_url}: {e}")

    # 8. Check for hints of Brute-Force Protection in headers of login page
    if relevant_headers:
        print("    [i] Checking login page headers for brute-force protection hints...")
        # Common headers related to rate limiting
        rate_limit_headers = ["X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After", "X-Retry-After"]
        found_bf_protection_header = False
        for header in rate_limit_headers:
            if header in relevant_headers:
                findings["brute_force_protection_hint"] = f"Detected Header: {header} = {relevant_headers[header]}"
                print(f"        [+] Found potential brute-force protection header: {header}: {relevant_headers[header]}")
                found_bf_protection_header = True
                break
        if not found_bf_protection_header:
            # Check for common plugin-specific headers if any (less common for GET on login page)
            # Example: Some plugins might set a cookie or a non-standard header
            if 'X-Powered-By' in relevant_headers and "Sucuri" in relevant_headers['X-Powered-By']: # Example
                 findings["brute_force_protection_hint"] = "Sucuri WAF detected (X-Powered-By), implies protection."
                 print("        [+] Sucuri WAF detected via X-Powered-By, implies brute-force protection.")
            else:
                findings["brute_force_protection_hint"] = "No direct headers found, relies on plugin logic or server config."
                print("        [-] No obvious rate-limiting headers found on login page GET response.")
    else:
        findings["brute_force_protection_hint"] = "No headers from login page to analyze."
        print("    [i] No login page headers available to check for brute-force protection hints.")


    # Finalize details for reporting
    details_parts = []
    if findings["standard_login_status"]["http_auth"] or findings["standard_admin_dir_status"]["http_auth"]:
        details_parts.append("HTTP Authentication detected on standard admin paths.")
        state.add_remediation_suggestion("admin_http_auth_info_v3", { # new key
            "source": "WP Analyzer (Admin Security)",
            "description": "HTTP Authentication (e.g., Basic/Digest) is used on standard admin paths (/wp-login.php or /wp-admin/), adding an additional layer of security before WordPress handles the request.",
            "severity": "Info",
            "remediation": "Ensure strong, unique credentials are used for HTTP Authentication. This is a good security practice to prevent direct access to WordPress login forms by bots."
        })

    if findings["standard_login_status"]["accessible"] is False:
        details_parts.append("Standard wp-login.php path appears inaccessible, hidden, or blocked.")
    elif findings["standard_login_status"]["accessible"] is True:
        details_parts.append("Standard wp-login.php path is accessible.")

    if findings["standard_admin_dir_status"]["accessible"] is False:
        details_parts.append("Standard wp-admin/ directory appears inaccessible or blocked.")
    elif findings["standard_admin_dir_status"]["accessible"] is True:
        details_parts.append("Standard wp-admin/ directory is accessible.")
    
    if findings["alternative_admin_paths_found"]:
        alt_paths_str = ", ".join([p["path"] for p in findings["alternative_admin_paths_found"]])
        details_parts.append(f"Found {len(findings['alternative_admin_paths_found'])} potential alternative admin path(s): {alt_paths_str}.")
        state.add_remediation_suggestion("admin_alt_paths_found_v2", {
            "source": "WP Analyzer (Admin Security)",
            "description": f"Potential alternative admin path(s) found: {alt_paths_str}. If these are active login pages, ensure they are adequately secured.",
            "severity": "Medium" if any(p["is_likely_login_page"] for p in findings["alternative_admin_paths_found"]) else "Low",
            "remediation": "If standard admin paths are intentionally hidden (e.g., by a security plugin), ensure the new paths are not easily guessable and are protected by strong passwords, 2FA, rate limiting, and CAPTCHA. Verify if these alternative paths are legitimate and intended."
        })

    if findings["detected_protection_plugins"]:
        plugins_str = ", ".join(findings["detected_protection_plugins"])
        details_parts.append(f"Detected footprints of admin/login protection plugin(s): {plugins_str}.")
        state.add_remediation_suggestion("admin_protection_plugins_detected_v2", {
            "source": "WP Analyzer (Admin Security)",
            "description": f"Footprints suggest the use of admin/login protection plugin(s): {plugins_str}. This is generally a good security measure.",
            "severity": "Info",
            "remediation": "Ensure any security plugins are kept up-to-date, configured correctly according to best practices, and are from reputable sources."
        })
    
    if findings["detected_captcha_services"]:
        captcha_str = ", ".join(findings["detected_captcha_services"])
        details_parts.append(f"Detected CAPTCHA service(s) on login page: {captcha_str}.")
        state.add_remediation_suggestion("admin_captcha_detected", {
            "source": "WP Analyzer (Admin Security)",
            "description": f"CAPTCHA service(s) ({captcha_str}) detected on the login page. This helps protect against automated login attempts.",
            "severity": "Info",
            "remediation": "Ensure CAPTCHA is functioning correctly and is implemented on all relevant forms (login, registration, password reset). Keep associated plugins updated."
        })

    if findings["detected_2fa_mechanisms"]:
        tfa_str = ", ".join(findings["detected_2fa_mechanisms"])
        details_parts.append(f"Detected hints of Two-Factor Authentication (2FA) mechanism(s): {tfa_str}.")
        state.add_remediation_suggestion("admin_2fa_detected", {
            "source": "WP Analyzer (Admin Security)",
            "description": f"Hints of Two-Factor Authentication (2FA) ({tfa_str}) detected. 2FA significantly enhances login security.",
            "severity": "Info",
            "remediation": "Encourage or enforce 2FA for all users, especially administrators. Ensure the 2FA method is robust and recovery codes are stored securely."
        })

    if findings["htaccess_protection_wp_admin"] not in ["Unknown", "Not Directly Accessible (404)", "Request Failed", "Error During Check"]:
        details_parts.append(f"wp-admin/.htaccess protection status: {findings['htaccess_protection_wp_admin']}.")
        # Add remediation if it's an unexpected status or implies misconfiguration
        if findings["htaccess_protection_wp_admin"].startswith("Unexpected Status"):
            state.add_remediation_suggestion("admin_htaccess_unexpected_status", {
                "source": "WP Analyzer (Admin Security)",
                "description": f"Accessing wp-admin/.htaccess returned an unexpected status: {findings['htaccess_protection_wp_admin']}. This might indicate a misconfiguration.",
                "severity": "Low",
                "remediation": "Review server configuration for /wp-admin/.htaccess to ensure it's behaving as expected. Typically, it should not be directly accessible (404) or return a 403 if protected."
            })
        elif findings["htaccess_protection_wp_admin"] == "Potentially Protected (403 Forbidden)":
             state.add_remediation_suggestion("admin_htaccess_403_info", {
                "source": "WP Analyzer (Admin Security)",
                "description": "Received 403 Forbidden for wp-admin/.htaccess, suggesting it might be present and its direct access is blocked. This is often a good sign.",
                "severity": "Info",
                "remediation": "Verify that if .htaccess is used for wp-admin protection, its rules are correctly configured and effective."
            })


    if findings["brute_force_protection_hint"] not in ["Unknown", "No headers from login page to analyze.", "No direct headers found, relies on plugin logic or server config."]:
        details_parts.append(f"Brute-force protection hint: {findings['brute_force_protection_hint']}.")
        state.add_remediation_suggestion("admin_brute_force_hint", {
            "source": "WP Analyzer (Admin Security)",
            "description": f"Hint of brute-force protection detected: {findings['brute_force_protection_hint']}. This is crucial for login security.",
            "severity": "Info",
            "remediation": "Ensure robust brute-force protection (e.g., via a security plugin or server-level tools like fail2ban) is active and configured with appropriate lockout thresholds and durations."
        })


    if not details_parts:
         details_parts.append("Admin area security checks run. Review specific findings for details.")

    findings["status"] = "Completed"
    findings["details"] = " ".join(filter(None, details_parts))
    all_wp_analyzer_findings = state.get_module_findings(module_key, {}) # Re-fetch
    all_wp_analyzer_findings[findings_key] = findings
    state.update_module_findings(module_key, all_wp_analyzer_findings)
    print(f"    [+] Admin area security advanced check finished. Details: {findings['details']}")
