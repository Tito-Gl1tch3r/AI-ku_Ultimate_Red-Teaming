# Module for WordPress Authentication Hardening Checks
from urllib.parse import urljoin
import requests # Retained for context
import re # Added import for re module
from .utils import make_request
import copy # Added for deepcopy

# Footprints for CAPTCHA plugins (expanded and enhanced)
CAPTCHA_FOOTPRINTS_AUTH = {
    "Google reCAPTCHA": [re.compile(r"google.com/recaptcha|grecaptcha|recaptcha-keys", re.IGNORECASE)],
    "hCaptcha": [re.compile(r"hcaptcha.com|h-captcha-response", re.IGNORECASE)],
    "Cloudflare Turnstile": [re.compile(r"challenges.cloudflare.com/turnstile|cf-turnstile", re.IGNORECASE)],
    "Really Simple CAPTCHA": [re.compile(r"really-simple-captcha", re.IGNORECASE)],
    "Math Captcha": [re.compile(r"math-captcha|wpcf7-math-captcha-form-control", re.IGNORECASE)],
    "Login No Captcha reCAPTCHA": [re.compile(r"login-nocaptcha", re.IGNORECASE)],
    "Captcha by BestWebSoft": [re.compile(r"bestwebsoft.*captcha|gglcptch", re.IGNORECASE)],
    "Advanced noCaptcha & invisible Captcha": [re.compile(r"anr_captcha|advanced-nocaptcha-recaptcha", re.IGNORECASE)],
    "Simple Login Captcha": [re.compile(r"simple-login-captcha", re.IGNORECASE)],
}

# Footprints for 2FA plugins (expanded and enhanced)
TFA_PLUGIN_FOOTPRINTS_AUTH = {
    "Wordfence Login Security (2FA)": [re.compile(r"wordfence-ls-|wf-ls-", re.IGNORECASE)], # Specific to Wordfence 2FA component
    "Google Authenticator (MiniOrange)": [re.compile(r"miniorange-2-factor|mo_2fa", re.IGNORECASE)],
    "Two Factor (WordPress Core Team)": [re.compile(r"Two Factor Authentication|#two-factor-backup-codes|#configure-two-factor", re.IGNORECASE)],
    "WP 2FA": [re.compile(r"wp-2fa-|wp2fa_", re.IGNORECASE)],
    "Solid Security (iThemes) 2FA": [re.compile(r"it-security.*2fa|itsec.*2fa|solid-security.*2fa", re.IGNORECASE)], # More specific to 2FA part of Solid/iThemes
    "All In One WP Security & Firewall (2FA)": [re.compile(r"aiowps_two_factor|aiowps-2fa", re.IGNORECASE)], # Specific to AIOWPS 2FA
    "Duo Two-Factor Authentication": [re.compile(r"duo_wordpress|duo-two-factor", re.IGNORECASE)],
    "Rublon Two-Factor Authentication": [re.compile(r"rublon|rublon-two-factor-authentication", re.IGNORECASE)],
    "Shield Security (2FA component)": [re.compile(r"icwp-wpsf.*feature-login_protect", re.IGNORECASE)], # Shield's login protection often includes 2FA
    "LoginPress - 2FA": [re.compile(r"loginpress-pro-2fa|lp_2fa", re.IGNORECASE)],
}

# Footprints for general Login Security / Hardening plugins (expanded and enhanced)
LOGIN_SECURITY_PLUGIN_FOOTPRINTS = {
    "Wordfence Security (General)": [re.compile(r"wordfence(?!-ls|-2fa)|wf_scan", re.IGNORECASE)], # General Wordfence, avoid double count with 2FA
    "Solid Security (iThemes Security)": [re.compile(r"solid-security|solid-wp-security|ithemes-security|it-security|itsec_", re.IGNORECASE)],
    "Sucuri Security": [re.compile(r"sucuri-scanner", re.IGNORECASE)],
    "All In One WP Security & Firewall (General)": [re.compile(r"aiowpsec|aiowps_", re.IGNORECASE)], # General AIOWPS
    "Limit Login Attempts Reloaded": [re.compile(r"limit-login-attempts-reloaded|llar_", re.IGNORECASE)],
    "WPS Hide Login": [re.compile(r"wps-hide-login", re.IGNORECASE)],
    "Loginizer": [re.compile(r"loginizer|lz_Cpatcha", re.IGNORECASE)],
    "WP Cerber Security": [re.compile(r"wp-cerber|crbr-", re.IGNORECASE)],
    "Defender Security": [re.compile(r"wp-defender|wdscan", re.IGNORECASE)],
    "Shield Security (General)": [re.compile(r"wp-simple-firewall|icwp-wpsf", re.IGNORECASE)],
    "Stop User Enumeration": [re.compile(r"stop-user-enumeration", re.IGNORECASE)],
    "WP Activity Log": [re.compile(r"wp-security-audit-log|wsal-", re.IGNORECASE)], # For monitoring auth attempts
    # Add more general login security plugin footprints
}


def _check_footprints(html_content, footprints_dict, category_name):
    """Helper to check for multiple footprints in HTML content."""
    detected = []
    if not html_content:
        return detected
    for name, patterns in footprints_dict.items():
        for pattern in patterns:
            if pattern.search(html_content):
                if name not in detected:
                    detected.append(name)
                    print(f"        [+] Detected {category_name} footprint: {name}")
                break # Found this specific plugin/type
    return detected


def analyze_auth_hardening(state, config, target_url):
    """
    Analyzes login page and related authentication hardening measures.
    Checks for CAPTCHA, 2FA, HTTP Auth, general security plugins, and clickjacking protection.
    """
    module_key = "wp_analyzer"
    findings_key = "auth_hardening"

    _DEFAULT_AUTH_HARDENING_FINDINGS = {
        "status": "Not Run",
        "details": "Performing authentication hardening checks...",
        "login_page_url": None,
        "login_page_accessible": None,
        "login_page_status_code_initial": None, # For the first response status before redirects
        "http_auth_on_login": False,
        "captcha_details": {"detected_types": [], "on_login_page": False, "on_lost_password_page": False},
        "tfa_plugin_footprints": [],
        "login_security_plugin_footprints": [],
        "clickjacking_protection_login": {"x_frame_options": None, "csp_frame_ancestors": None},
        "referrer_policy_login": None, # New: Referrer-Policy header on login page
        "lost_password_page_accessible": None,
        "password_policy_strength": {"status": "Informational", "details": "Password policy strength is best assessed through configuration review or authenticated testing."},
        "account_lockout_mechanism": {"status": "Informational", "details": "Account lockout mechanisms are difficult to confirm reliably without potentially disruptive active login attempts."},
        "custom_login_url_suspected": {"status": "Not Determined", "details": "Indicates if wp-login.php is inaccessible and a login hiding plugin might be active."}, # New
        "security_questions_on_reset": {"status": "Not Determined", "details": "Security questions on password reset are not currently checked."}, # New placeholder
        "session_cookie_attributes": {"http_only": "Not Checked", "secure_flag": "Not Checked", "samesite": "Not Checked"} # New placeholder
    }

    all_wp_analyzer_findings_raw = state.get_module_findings(module_key, {})
    if not isinstance(all_wp_analyzer_findings_raw, dict):
        all_wp_analyzer_findings = {}
    else:
        all_wp_analyzer_findings = all_wp_analyzer_findings_raw
        
    existing_findings = all_wp_analyzer_findings.get(findings_key, {})

    findings = copy.deepcopy(_DEFAULT_AUTH_HARDENING_FINDINGS)

    if isinstance(existing_findings, dict):
        for key, value in existing_findings.items():
            if key in findings: # Only update if key is part of the default structure
                if isinstance(findings[key], dict) and isinstance(value, dict):
                    findings[key].update(value) # Merge nested dicts
                elif isinstance(findings[key], list) and isinstance(value, list):
                    findings[key].extend(v for v in value if v not in findings[key]) # Merge lists, avoid duplicates
                else:
                    findings[key] = value # Overwrite for simple types or if types don't match for merging

    findings["status"] = "Running" # Always set status for the current run
    
    all_wp_analyzer_findings[findings_key] = findings
    state.update_module_findings(module_key, all_wp_analyzer_findings) # Save initial state

    print("    [i] Analyzing Authentication Hardening...")
    login_url = urljoin(target_url, 'wp-login.php')
    findings["login_page_url"] = login_url
    login_page_html = None
    login_page_headers = {}

    # 1. Check wp-login.php accessibility and HTTP Auth
    print(f"      Checking accessibility and HTTP Auth for: {login_url}")
    try:
        # Check without redirects first for HTTP Auth
        response_no_redirect = make_request(login_url, config, method="GET", allow_redirects=False, timeout=7)
        if response_no_redirect:
            findings["login_page_status_code_initial"] = response_no_redirect.status_code
            if response_no_redirect.status_code == 401:
                findings["http_auth_on_login"] = True
                print("        [+] HTTP Authentication detected on wp-login.php.")
                # If HTTP auth, still try to get content if a subsequent request (e.g. by a browser with creds) would work
                # For this script, we assume if 401, we can't proceed to get HTML content easily.
            elif 200 <= response_no_redirect.status_code < 400 : # Includes 200 OK or redirects
                 # Now fetch with redirects to get the final login page content
                response_final = make_request(login_url, config, method="GET", allow_redirects=True, timeout=10)
                if response_final and response_final.status_code == 200:
                    if "user_login" in response_final.text and "user_pass" in response_final.text:
                        findings["login_page_accessible"] = True
                        login_page_html = response_final.text
                        login_page_headers = response_final.headers
                        print(f"        [+] Login page accessible at {response_final.url}.")
                    else:
                        findings["login_page_accessible"] = "Partial (Content Mismatch)"
                        print(f"        [?] Login page at {response_final.url} returned 200 but content doesn't match standard form.")
                elif response_final:
                    findings["login_page_accessible"] = False
                    print(f"        [-] Login page final request failed or non-200: Status {response_final.status_code} at {response_final.url}")
                else:
                    findings["login_page_accessible"] = False; print("        [-] Failed to fetch final login page after initial check.")
            else: # 403, 404, 5xx on initial request
                findings["login_page_accessible"] = False
                print(f"        [-] wp-login.php not accessible or blocked (Initial Status: {response_no_redirect.status_code}).")
        else:
            findings["login_page_accessible"] = False; print("        [-] Request to wp-login.php failed (no initial response).")
    except Exception as e:
        print(f"      [-] Error checking login page: {e}")
        findings["login_page_accessible"] = "Error"
        findings["login_page_status_code_initial"] = f"Error: {type(e).__name__}"

    # 2. Analyze Login Page HTML if fetched
    if login_page_html:
        findings["captcha_details"]["on_login_page"] = True # Assume we are checking login page if HTML is present
        detected_captcha_types = _check_footprints(login_page_html, CAPTCHA_FOOTPRINTS_AUTH, "CAPTCHA")
        if detected_captcha_types:
            findings["captcha_details"]["detected_types"].extend(dt for dt in detected_captcha_types if dt not in findings["captcha_details"]["detected_types"])
        
        detected_tfa_plugins = _check_footprints(login_page_html, TFA_PLUGIN_FOOTPRINTS_AUTH, "2FA Plugin")
        findings["tfa_plugin_footprints"].extend(dt for dt in detected_tfa_plugins if dt not in findings["tfa_plugin_footprints"])

        detected_sec_plugins = _check_footprints(login_page_html, LOGIN_SECURITY_PLUGIN_FOOTPRINTS, "Login Security Plugin")
        findings["login_security_plugin_footprints"].extend(dt for dt in detected_sec_plugins if dt not in findings["login_security_plugin_footprints"])

        # Clickjacking Protection
        findings["clickjacking_protection_login"]["x_frame_options"] = login_page_headers.get('X-Frame-Options', 'Not Set')
        csp_header = login_page_headers.get('Content-Security-Policy', 'Not Set')
        if 'frame-ancestors' in csp_header:
            findings["clickjacking_protection_login"]["csp_frame_ancestors"] = csp_header # Store the full CSP if frame-ancestors is present
            print(f"        [+] CSP with frame-ancestors found on login page: {csp_header}")
        elif csp_header != 'Not Set': # CSP exists but no frame-ancestors
            findings["clickjacking_protection_login"]["csp_frame_ancestors"] = "Present, but 'frame-ancestors' directive missing."
            print(f"        [?] CSP found, but 'frame-ancestors' directive missing: {csp_header}")
        else: # No CSP header
            findings["clickjacking_protection_login"]["csp_frame_ancestors"] = 'Not Set'

        if findings["clickjacking_protection_login"]["x_frame_options"] != 'Not Set':
             print(f"        [+] X-Frame-Options found on login page: {findings['clickjacking_protection_login']['x_frame_options']}")
        
        if findings["clickjacking_protection_login"]["x_frame_options"] == 'Not Set' and 'frame-ancestors' not in findings["clickjacking_protection_login"]["csp_frame_ancestors"]:
             print("        [-] Login page appears vulnerable to Clickjacking (Missing X-Frame-Options or CSP frame-ancestors).")
        
        # Referrer-Policy Check
        findings["referrer_policy_login"] = login_page_headers.get('Referrer-Policy', 'Not Set')
        if findings["referrer_policy_login"] != 'Not Set':
            print(f"        [+] Referrer-Policy found on login page: {findings['referrer_policy_login']}")
        else:
            print("        [-] Referrer-Policy header not found on login page.")


    # 3. Password Reset Page Analysis (wp-login.php?action=lostpassword)
    lostpassword_url = urljoin(target_url, 'wp-login.php?action=lostpassword')
    print(f"      Checking password reset page: {lostpassword_url}")
    lostpassword_page_html = None
    try:
        response_lp = make_request(lostpassword_url, config, method="GET", timeout=7)
        if response_lp and response_lp.status_code == 200:
            findings["lost_password_page_accessible"] = True
            lostpassword_page_html = response_lp.text
            print(f"        [+] Password reset page accessible at {lostpassword_url}.")
            # Check for CAPTCHA on lost password page
            if lostpassword_page_html:
                findings["captcha_details"]["on_lost_password_page"] = True
                detected_lp_captcha_types = _check_footprints(lostpassword_page_html, CAPTCHA_FOOTPRINTS_AUTH, "CAPTCHA on Lost Password Page")
                if detected_lp_captcha_types: # Add to overall list, avoid duplicates
                    for dt in detected_lp_captcha_types:
                        if dt not in findings["captcha_details"]["detected_types"]:
                             findings["captcha_details"]["detected_types"].append(dt)
        elif response_lp:
            findings["lost_password_page_accessible"] = False
            print(f"        [-] Password reset page not accessible or error (Status: {response_lp.status_code}).")
        else:
            findings["lost_password_page_accessible"] = False; print("        [-] Request to password reset page failed.")
    except Exception as e:
        print(f"      [-] Error checking password reset page: {e}")
        findings["lost_password_page_accessible"] = "Error"

    # Consolidate details and add remediations
    summary = []
    # Update custom_login_url_suspected status
    if findings["login_page_accessible"] == False and findings.get("login_page_status_code_initial") == 404:
        findings["custom_login_url_suspected"]["status"] = "Suspected"
        findings["custom_login_url_suspected"]["details"] = "wp-login.php returned 404. The login page may have been moved (e.g., by a security plugin). This requires further investigation or knowledge of site configuration."
        if 'WPS Hide Login' in findings["login_security_plugin_footprints"]: # This check is weak if login_page_html is None
             findings["custom_login_url_suspected"]["details"] += " 'WPS Hide Login' or similar plugin might be active."
    elif findings["login_page_accessible"] == True :
        findings["custom_login_url_suspected"]["status"] = "Not Suspected"
        findings["custom_login_url_suspected"]["details"] = "Standard wp-login.php is accessible."


    # Consolidate details and add remediations
    summary = []
    if findings["http_auth_on_login"]:
        summary.append("HTTP Authentication is enabled on wp-login.php.")
        state.add_remediation_suggestion("auth_http_login", {"source":"AuthHardening", "description":"HTTP Auth on login page.", "severity":"Info", "remediation":"Good practice. Ensure strong credentials."})
    
    if findings["captcha_details"]["detected_types"]:
        types = ", ".join(findings["captcha_details"]["detected_types"])
        summary.append(f"CAPTCHA ({types}) detected.")
        state.add_remediation_suggestion("auth_captcha_present", {"source":"AuthHardening", "description":f"CAPTCHA ({types}) detected.", "severity":"Info", "remediation":"Good. Ensure it's effective and up-to-date."})
    else:
        summary.append("No common CAPTCHA detected on login or lost password pages.")
        state.add_remediation_suggestion("auth_captcha_missing", {"source":"AuthHardening", "description":"No CAPTCHA detected on login/lost password pages.", "severity":"Low", "remediation":"Consider adding CAPTCHA to login and password reset forms to protect against automated attacks."})

    if findings["tfa_plugin_footprints"]:
        summary.append(f"2FA plugin footprints detected: {', '.join(findings['tfa_plugin_footprints'])}.")
        state.add_remediation_suggestion("auth_tfa_plugins", {"source":"AuthHardening", "description":"2FA plugin footprints detected.", "severity":"Info", "remediation":"Good. Ensure 2FA is enforced for all users, especially administrators."})
    else:
        summary.append("No clear 2FA plugin footprints detected on the login page.")
        state.add_remediation_suggestion("auth_tfa_missing", {"source":"AuthHardening", "description":"No 2FA plugin footprints detected.", "severity":"Medium", "remediation":"Consider implementing Two-Factor Authentication (2FA) for all users, especially administrators, to significantly enhance login security."})


    if findings["login_security_plugin_footprints"]:
        summary.append(f"General login security plugin footprints: {', '.join(findings['login_security_plugin_footprints'])}.")
    
    # Clickjacking
    xfo = findings["clickjacking_protection_login"]["x_frame_options"]
    csp_fa = findings["clickjacking_protection_login"]["csp_frame_ancestors"]
    clickjacking_protected = not (xfo == 'Not Set' and ('frame-ancestors' not in csp_fa or csp_fa == 'Not Set'))
    if not clickjacking_protected:
        summary.append("Login page may be vulnerable to clickjacking (Missing X-Frame-Options or CSP 'frame-ancestors').")
        state.add_remediation_suggestion("auth_clickjacking_login", {"source":"AuthHardening", "description":"Login page clickjacking protection (X-Frame-Options or CSP frame-ancestors) is missing or insufficient.", "severity":"Medium", "remediation":"Implement X-Frame-Options (e.g., 'DENY' or 'SAMEORIGIN') or Content-Security-Policy 'frame-ancestors' directive (e.g., 'self' or 'none') on the login page to prevent clickjacking attacks."})
    else:
        summary.append("Login page has clickjacking protection (X-Frame-Options or CSP 'frame-ancestors').")

    # Referrer-Policy
    rp = findings["referrer_policy_login"]
    if rp == 'Not Set' or rp in ['unsafe-url', 'no-referrer-when-downgrade']: # Less strict policies
        summary.append(f"Referrer-Policy on login page is '{rp}'. Consider a stricter policy.")
        state.add_remediation_suggestion("auth_referrer_policy_login_weak", {"source":"AuthHardening", "description":f"Login page Referrer-Policy is '{rp}'.", "severity":"Low", "remediation":"Set a stricter Referrer-Policy (e.g., 'strict-origin-when-cross-origin', 'same-origin', or 'no-referrer') on the login page to prevent leaking sensitive information via the Referer header."})
    else:
        summary.append(f"Referrer-Policy on login page is set to '{rp}'.")

    if findings["custom_login_url_suspected"]["status"] == "Suspected":
        summary.append(findings["custom_login_url_suspected"]["details"])


    findings["details"] = " ".join(summary) if summary else "Auth hardening checks performed. See specific findings."
    findings["status"] = "Completed"
    all_wp_analyzer_findings = state.get_module_findings(module_key, {}) # Re-fetch
    all_wp_analyzer_findings[findings_key] = findings
    state.update_module_findings(module_key, all_wp_analyzer_findings)
    print(f"    [+] Authentication hardening checks finished. Details: {findings['details']}")
