# Module for In-depth WordPress Configuration Audits
import requests
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup # Not strictly needed for current remote checks, but retained
from .utils import make_request
import copy # Added for deepcopy

def analyze_configuration(state, config, target_url):
    """
    Performs remote heuristic checks for WordPress configuration settings.
    Checks for WP_DEBUG exposure, DISALLOW_FILE_EDIT, FORCE_SSL_ADMIN hints.
    DB prefix, security keys, file permissions, .htaccess content are not reliably checkable remotely.
    """
    module_key = "wp_analyzer"
    findings_key = "configuration_audit"

    # Define the canonical/default structure for this specific audit's findings
    _DEFAULT_CONFIG_AUDIT_STRUCTURE = {
        "status": "Not Run",
        "details": "Configuration audit checks pending.",
        "wp_debug_check": {"status": "Not Run", "debug_mode_active_hint": None, "display_errors_hint": None, "log_path_exposed": None},
        "disallow_file_edit_check": {"status": "Not Run", "likely_false": None},
        "force_ssl_admin_check": {"status": "Not Run", "likely_true": None},
        "wp_config_backup_check": {"status": "Not Run", "exposed_paths": [], "details": "Checking for exposed wp-config.php backup files..."},
        "htaccess_backup_check": {"status": "Not Run", "exposed_paths": [], "details": "Checking for exposed .htaccess backup files..."},
        "debug_log_access_check": {"status": "Not Run", "accessible": None, "path": "wp-content/debug.log", "details": "Checking for direct access to debug.log..."},
        "phpinfo_check": {"status": "Not Run", "exposed_path": None, "details": "Checking for exposed phpinfo.php file..."},
        "db_prefix_check": {"status": "Informational", "message": "DB prefix cannot be reliably determined remotely. Using a non-default prefix is recommended."},
        "security_keys_check": {"status": "Informational", "message": "Security keys/salts in wp-config.php cannot be checked remotely. Ensure they are unique and strong."},
        "file_permissions_check": {"status": "Informational", "message": "File permissions (wp-config.php, .htaccess) cannot be checked remotely. Ensure they are hardened."},
        "htaccess_rules_check": {"status": "Informational", "message": "Custom .htaccess security rules cannot be verified remotely. Review manually if applicable."}
    }

    all_wp_analyzer_findings_raw = state.get_module_findings(module_key, {})
    if not isinstance(all_wp_analyzer_findings_raw, dict):
        all_wp_analyzer_findings = {}
        # Optionally log state corruption
        # state.add_tool_error(f"Warning: Findings for module '{module_key}' were not a dictionary. Resetting for '{findings_key}'.")
    else:
        all_wp_analyzer_findings = all_wp_analyzer_findings_raw
        
    existing_findings = all_wp_analyzer_findings.get(findings_key, {})

    # Start with a deep copy of the default structure
    findings = copy.deepcopy(_DEFAULT_CONFIG_AUDIT_STRUCTURE)

    # Update with existing findings if they are a dictionary
    if isinstance(existing_findings, dict):
        for key, value in existing_findings.items():
            # For nested dictionaries (sub-checks), merge them carefully
            if key in findings and isinstance(findings[key], dict) and isinstance(value, dict):
                findings[key].update(value)
            # For other top-level keys in the default structure
            elif key in findings:
                findings[key] = value
            # Keys from existing_findings not in _DEFAULT_CONFIG_AUDIT_STRUCTURE are ignored.
    
    findings["status"] = "Running" # Always set status for the current run

    # Ensure all sub-check keys from default structure exist and have at least a status and message if applicable
    # This also handles the case where existing_findings might have been incomplete or malformed for sub-checks
    for sub_key in _DEFAULT_CONFIG_AUDIT_STRUCTURE.keys():
        if sub_key not in ["status", "details"]: # These are top-level, not sub-checks
            if sub_key not in findings or not isinstance(findings[sub_key], dict): # If sub_key missing or not a dict
                findings[sub_key] = copy.deepcopy(_DEFAULT_CONFIG_AUDIT_STRUCTURE[sub_key]) # Re-initialize from default
            else: # Sub_key exists and is a dict, ensure 'status' and 'message' (if in default) are present
                if "status" not in findings[sub_key]:
                    findings[sub_key]["status"] = _DEFAULT_CONFIG_AUDIT_STRUCTURE[sub_key].get("status", "Not Run")
                if "message" in _DEFAULT_CONFIG_AUDIT_STRUCTURE[sub_key] and "message" not in findings[sub_key]:
                    findings[sub_key]["message"] = _DEFAULT_CONFIG_AUDIT_STRUCTURE[sub_key]["message"]
    
    all_wp_analyzer_findings[findings_key] = findings
    state.update_module_findings(module_key, all_wp_analyzer_findings) # Save initial state

    print("\n    [i] Performing WordPress Configuration Audit (Remote Heuristics)...")

    # 1. WP_DEBUG Detection Heuristic
    print("      Attempting to detect WP_DEBUG exposure...")
    findings["wp_debug_check"]["status"] = "Running"
    debug_test_url = urljoin(target_url, "wp-content/this-file-should-not-exist-debug-check.php")
    try:
        debug_response = make_request(debug_test_url, config, method="GET", timeout=5)
        if debug_response and debug_response.text:
            # Common patterns indicating debug mode / display_errors is on
            # WordPress often shows "Warning:", "Notice:", "Fatal error:" with file paths.
            # PHP's display_errors might show "<b>Warning</b>:", "<b>Notice</b>:", etc.
            wp_debug_patterns = [
                re.compile(r"(<b>)?(Warning|Notice|Fatal error)(</b>)?:\s+.+?\s+in\s+<b>.+?</b>\s+on\s+line\s+<b>\d+</b>", re.IGNORECASE),
                re.compile(r"display_errors\s*=\s*on", re.IGNORECASE) # If phpinfo() or similar is exposed
            ]
            php_error_signature = re.compile(r"<br\s*/?>\s*\n(<b>)?(Warning|Notice|Fatal error|Parse error)(</b>)?:", re.IGNORECASE)

            if php_error_signature.search(debug_response.text):
                findings["wp_debug_check"]["debug_mode_active_hint"] = True
                findings["wp_debug_check"]["display_errors_hint"] = True # If PHP errors are displayed, display_errors is likely on
                print("        [!] Potential WP_DEBUG or display_errors exposure: Verbose PHP errors detected.")
                
                # Check for log path exposure (less common from this specific test)
                log_path_match = re.search(r"WordPress database error .* for query .* made by .* PHP Stack trace: .* PHP .* WP_DEBUG_LOG", debug_response.text, re.IGNORECASE | re.DOTALL)
                if log_path_match:
                     findings["wp_debug_check"]["log_path_exposed"] = True # Or extract path if possible
                     print("        [!] Potential WP_DEBUG_LOG path exposure in error message.")
            else:
                findings["wp_debug_check"]["debug_mode_active_hint"] = False
                findings["wp_debug_check"]["display_errors_hint"] = False
                print("        [-] No clear signs of WP_DEBUG or display_errors exposure from test URL.")
        else:
            print("        [-] Could not get a response from debug test URL or response was empty.")
            findings["wp_debug_check"]["status"] = "Error (No Response)"
    except Exception as e:
        print(f"        [-] Error during WP_DEBUG check: {e}")
        findings["wp_debug_check"]["status"] = f"Error ({type(e).__name__})"
    if findings["wp_debug_check"]["status"] == "Running": findings["wp_debug_check"]["status"] = "Completed"


    # 2. DISALLOW_FILE_EDIT Heuristic
    print("      Attempting to infer DISALLOW_FILE_EDIT setting...")
    findings["disallow_file_edit_check"]["status"] = "Running"
    # If these redirect to login, file editing is likely enabled (default)
    # If 403/404 or specific message, it might be disabled.
    # This is a weak heuristic without an authenticated session.
    editor_paths_to_check = {
        "theme_editor": urljoin(target_url, "wp-admin/theme-editor.php"),
        "plugin_editor": urljoin(target_url, "wp-admin/plugin-editor.php")
    }
    editors_seem_enabled = 0
    editors_checked = 0
    for editor_key, editor_url in editor_paths_to_check.items():
        editors_checked += 1
        try:
            editor_response = make_request(editor_url, config, method="GET", allow_redirects=False, timeout=5) # Don't follow redirects initially
            if editor_response and editor_response.status_code in [301, 302, 303, 307, 308]:
                redirect_loc = editor_response.headers.get("Location", "")
                if "wp-login.php" in redirect_loc:
                    editors_seem_enabled +=1
                    print(f"        [i] {editor_key} ({editor_url}) redirects to login. Suggests file editor might be enabled (DISALLOW_FILE_EDIT likely false).")
                # else: redirects elsewhere, inconclusive for this check
            # else: 200 (unlikely unauth), 403, 404 - inconclusive or suggests disabled
        except Exception as e:
            print(f"        [-] Error checking {editor_key} at {editor_url}: {e}")
            findings["disallow_file_edit_check"]["status"] = f"Error checking {editor_key} ({type(e).__name__})"
            break 
    
    if findings["disallow_file_edit_check"]["status"] == "Running": # No error during loop
        if editors_checked > 0 and editors_seem_enabled == editors_checked:
            findings["disallow_file_edit_check"]["likely_false"] = True # True means DISALLOW_FILE_EDIT is likely false (editors enabled)
            print("        [!] DISALLOW_FILE_EDIT seems to be false (editors enabled).")
        elif editors_checked > 0 and editors_seem_enabled == 0:
            # This could mean they are disabled OR simply not redirecting to login (e.g. custom 404/403)
            findings["disallow_file_edit_check"]["likely_false"] = False # Heuristic: if no redirect to login, assume disabled or protected
            print("        [+] DISALLOW_FILE_EDIT seems to be true (editors likely disabled or access restricted).")
        else: # Mixed results or errors
            findings["disallow_file_edit_check"]["likely_false"] = None # Undetermined
            print("        [?] DISALLOW_FILE_EDIT status is undetermined from remote checks.")
        findings["disallow_file_edit_check"]["status"] = "Completed"


    # 3. FORCE_SSL_ADMIN Heuristic
    print("      Attempting to infer FORCE_SSL_ADMIN setting...")
    findings["force_ssl_admin_check"]["status"] = "Running"
    parsed_target = urlparse(target_url)
    if parsed_target.scheme == "http":
        admin_http_url = urljoin(target_url, "wp-admin/")
        try:
            ssl_response = make_request(admin_http_url, config, method="GET", allow_redirects=False, timeout=5)
            if ssl_response and ssl_response.status_code in [301, 302, 303, 307, 308]:
                redirect_loc = ssl_response.headers.get("Location", "")
                if redirect_loc.startswith("https://"):
                    findings["force_ssl_admin_check"]["likely_true"] = True
                    print("        [+] HTTP wp-admin access redirects to HTTPS. FORCE_SSL_ADMIN likely true or server-level HTTPS enforcement.")
                else:
                    findings["force_ssl_admin_check"]["likely_true"] = False
                    print("        [-] HTTP wp-admin access redirects, but not to HTTPS.")
            elif ssl_response: # No redirect, or error
                 findings["force_ssl_admin_check"]["likely_true"] = False
                 print(f"        [-] HTTP wp-admin access did not redirect to HTTPS (Status: {ssl_response.status_code}).")
            else:
                findings["force_ssl_admin_check"]["status"] = "Error (No Response)"
        except Exception as e:
            print(f"        [-] Error during FORCE_SSL_ADMIN check: {e}")
            findings["force_ssl_admin_check"]["status"] = f"Error ({type(e).__name__})"
    else: # Target URL is already HTTPS
        findings["force_ssl_admin_check"]["likely_true"] = None # Cannot determine if already HTTPS
        findings["force_ssl_admin_check"]["message"] = "Target URL is already HTTPS, FORCE_SSL_ADMIN relevance is for HTTP sites."
        print("        [i] Target URL is already HTTPS. FORCE_SSL_ADMIN check is primarily for HTTP sites.")
    if findings["force_ssl_admin_check"]["status"] == "Running": findings["force_ssl_admin_check"]["status"] = "Completed"

    # 4. wp-config.php Backup File Check
    print("      Attempting to find exposed wp-config.php backup files...")
    findings["wp_config_backup_check"]["status"] = "Running"
    config_backup_suffixes = ['.bak', '.old', '.txt', '~', '.save', '.swp', '_backup', '-backup', '.tmp', '.copy', '.orig']
    config_base_path = "wp-config.php" 
    exposed_config_backups = []
    for suffix in config_backup_suffixes:
        backup_path = config_base_path + suffix
        backup_url = urljoin(target_url, backup_path)
        try:
            response = make_request(backup_url, config, method="GET", timeout=3)
            if response and response.status_code == 200 and "DB_NAME" in response.text and "DB_USER" in response.text:
                print(f"        [!!!] CRITICAL: Exposed wp-config.php backup found: {backup_url}")
                exposed_config_backups.append(backup_url)
            # else: print(f"        [-] No exposed wp-config.php backup at {backup_url} (Status: {response.status_code if response else 'No response'})")
        except Exception as e:
            print(f"        [-] Error checking {backup_url}: {e}")
    findings["wp_config_backup_check"]["exposed_paths"] = exposed_config_backups
    if exposed_config_backups:
        findings["wp_config_backup_check"]["details"] = f"CRITICAL: Found {len(exposed_config_backups)} exposed wp-config.php backup(s)."
    else:
        findings["wp_config_backup_check"]["details"] = "No exposed wp-config.php backup files found."
    findings["wp_config_backup_check"]["status"] = "Completed"

    # 5. .htaccess Backup File Check
    print("      Attempting to find exposed .htaccess backup files...")
    findings["htaccess_backup_check"]["status"] = "Running"
    htaccess_backup_suffixes = ['.bak', '.old', '.txt', '~', '.save', '_backup', '-backup', '.tmp', '.copy', '.orig']
    # Common .htaccess locations (root is most common)
    htaccess_base_paths = [".htaccess", "wp-admin/.htaccess", "wp-content/.htaccess", "wp-includes/.htaccess"]
    exposed_htaccess_backups = []
    for base_path in htaccess_base_paths:
        for suffix in htaccess_backup_suffixes:
            backup_path = base_path + suffix
            backup_url = urljoin(target_url, backup_path)
            try:
                response = make_request(backup_url, config, method="GET", timeout=3)
                # .htaccess content is varied, look for common directives or just 200 OK and non-empty
                if response and response.status_code == 200 and response.text and ("RewriteRule" in response.text or "Options" in response.text or "Order allow,deny" in response.text):
                    print(f"        [!!] HIGH: Exposed .htaccess backup found: {backup_url}")
                    exposed_htaccess_backups.append(backup_url)
                # else: print(f"        [-] No exposed .htaccess backup at {backup_url} (Status: {response.status_code if response else 'No response'})")
            except Exception as e:
                print(f"        [-] Error checking {backup_url}: {e}")
    findings["htaccess_backup_check"]["exposed_paths"] = exposed_htaccess_backups
    if exposed_htaccess_backups:
        findings["htaccess_backup_check"]["details"] = f"HIGH: Found {len(exposed_htaccess_backups)} exposed .htaccess backup(s)."
    else:
        findings["htaccess_backup_check"]["details"] = "No exposed .htaccess backup files found."
    findings["htaccess_backup_check"]["status"] = "Completed"

    # 6. Debug Log Access Check
    print("      Attempting to access wp-content/debug.log...")
    findings["debug_log_access_check"]["status"] = "Running"
    debug_log_url = urljoin(target_url, findings["debug_log_access_check"]["path"])
    try:
        response = make_request(debug_log_url, config, method="GET", timeout=5)
        if response and response.status_code == 200 and response.text: # Check if non-empty
            findings["debug_log_access_check"]["accessible"] = True
            findings["debug_log_access_check"]["details"] = "Potentially sensitive debug.log is publicly accessible."
            print(f"        [!!] HIGH: {findings['debug_log_access_check']['path']} is publicly accessible and contains data.")
        elif response and response.status_code == 200: # Empty but accessible
            findings["debug_log_access_check"]["accessible"] = True # Technically accessible
            findings["debug_log_access_check"]["details"] = "debug.log is publicly accessible but appears empty."
            print(f"        [!] WARNING: {findings['debug_log_access_check']['path']} is publicly accessible (currently empty).")
        else:
            findings["debug_log_access_check"]["accessible"] = False
            findings["debug_log_access_check"]["details"] = "debug.log does not appear to be publicly accessible or is empty."
            print(f"        [-] {findings['debug_log_access_check']['path']} not accessible or empty (Status: {response.status_code if response else 'No Response'}).")
    except Exception as e:
        print(f"        [-] Error checking debug.log: {e}")
        findings["debug_log_access_check"]["status"] = f"Error ({type(e).__name__})"
        findings["debug_log_access_check"]["details"] = f"Error checking debug.log: {e}"
    if findings["debug_log_access_check"]["status"] == "Running": findings["debug_log_access_check"]["status"] = "Completed"

    # 7. phpinfo.php Exposure Check
    print("      Attempting to find exposed phpinfo.php file...")
    findings["phpinfo_check"]["status"] = "Running"
    phpinfo_paths = ["phpinfo.php", "info.php", "test.php", "wp-admin/phpinfo.php", "admin/phpinfo.php"]
    exposed_phpinfo_path = None
    for path in phpinfo_paths:
        phpinfo_url = urljoin(target_url, path)
        try:
            response = make_request(phpinfo_url, config, method="GET", timeout=3)
            if response and response.status_code == 200 and "phpinfo()" in response.text and "PHP Version" in response.text:
                print(f"        [!!!] CRITICAL: Exposed phpinfo() output found at: {phpinfo_url}")
                exposed_phpinfo_path = phpinfo_url
                break 
            # else: print(f"        [-] No phpinfo() at {phpinfo_url} (Status: {response.status_code if response else 'No response'})")
        except Exception as e:
            print(f"        [-] Error checking {phpinfo_url}: {e}")
    
    findings["phpinfo_check"]["exposed_path"] = exposed_phpinfo_path
    if exposed_phpinfo_path:
        findings["phpinfo_check"]["details"] = f"CRITICAL: phpinfo() output exposed at {exposed_phpinfo_path}."
    else:
        findings["phpinfo_check"]["details"] = "No exposed phpinfo.php file found."
    findings["phpinfo_check"]["status"] = "Completed"


    # Update overall details and add remediations
    details_summary = []
    if findings["wp_debug_check"]["debug_mode_active_hint"]:
        details_summary.append("WP_DEBUG/display_errors exposure hinted.")
        state.add_remediation_suggestion("wp_debug_exposed", {
            "source": "WP Analyzer (Config Audit)",
            "description": "Potential exposure of verbose PHP errors, suggesting WP_DEBUG and/or display_errors might be enabled on a production site.",
            "severity": "Medium",
            "remediation": "Ensure WP_DEBUG, WP_DEBUG_LOG, and WP_DEBUG_DISPLAY are set to false on production sites to prevent information leakage. If debugging is needed, enable logging to a private file instead of displaying errors."
        })
    
    if findings["disallow_file_edit_check"]["likely_false"] is True:
        details_summary.append("DISALLOW_FILE_EDIT is likely false (editors enabled).")
        state.add_remediation_suggestion("disallow_file_edit_false", {
            "source": "WP Analyzer (Config Audit)",
            "description": "The DISALLOW_FILE_EDIT constant in wp-config.php appears to be false or not set, meaning theme/plugin editors are enabled in wp-admin.",
            "severity": "Low",
            "remediation": "Set define('DISALLOW_FILE_EDIT', true); in wp-config.php to disable theme and plugin editors. This can prevent an attacker from easily modifying code if they gain admin access."
        })
    elif findings["disallow_file_edit_check"]["likely_false"] is False: # Explicitly seems disabled
         details_summary.append("DISALLOW_FILE_EDIT is likely true (editors disabled/restricted).")

    if findings["wp_config_backup_check"]["exposed_paths"]:
        details_summary.append(f"CRITICAL: Exposed wp-config.php backup(s) found: {', '.join(findings['wp_config_backup_check']['exposed_paths'])}.")
        state.add_remediation_suggestion("wp_config_backup_exposed", {
            "source": "WP Analyzer (Config Audit)",
            "description": f"Publicly accessible backup(s) of wp-config.php found: {', '.join(findings['wp_config_backup_check']['exposed_paths'])}. This file contains database credentials and security keys.",
            "severity": "Critical",
            "remediation": "Immediately remove any publicly accessible backup copies of wp-config.php. Ensure web server configuration prevents listing or direct access to backup files. Review backup procedures to store backups securely."
        })

    if findings["htaccess_backup_check"]["exposed_paths"]:
        details_summary.append(f"HIGH: Exposed .htaccess backup(s) found: {', '.join(findings['htaccess_backup_check']['exposed_paths'])}.")
        state.add_remediation_suggestion("htaccess_backup_exposed", {
            "source": "WP Analyzer (Config Audit)",
            "description": f"Publicly accessible backup(s) of .htaccess file(s) found: {', '.join(findings['htaccess_backup_check']['exposed_paths'])}. This file can control web server behavior and security settings.",
            "severity": "High",
            "remediation": "Immediately remove any publicly accessible backup copies of .htaccess files. Ensure web server configuration prevents listing or direct access to backup files."
        })

    if findings["debug_log_access_check"]["accessible"] and "Potentially sensitive debug.log is publicly accessible." in findings["debug_log_access_check"]["details"]: # Check for non-empty case
        details_summary.append(f"HIGH: {findings['debug_log_access_check']['path']} is publicly accessible and contains data.")
        state.add_remediation_suggestion("debug_log_accessible", {
            "source": "WP Analyzer (Config Audit)",
            "description": f"The WordPress debug log ({findings['debug_log_access_check']['path']}) is publicly accessible and contains information. This can leak sensitive details about your website, plugins, themes, and server environment.",
            "severity": "High",
            "remediation": "Disable public access to debug.log (e.g., via .htaccess or server configuration). Ensure WP_DEBUG_LOG is false on production sites, or if used, that the log path is not web-accessible. Regularly review and clear the debug log."
        })
    elif findings["debug_log_access_check"]["accessible"]: # Empty but accessible
        details_summary.append(f"WARNING: {findings['debug_log_access_check']['path']} is publicly accessible (currently empty).")
        state.add_remediation_suggestion("debug_log_accessible_empty", {
            "source": "WP Analyzer (Config Audit)",
            "description": f"The WordPress debug log ({findings['debug_log_access_check']['path']}) is publicly accessible but currently appears empty. If WP_DEBUG_LOG is enabled, it could expose sensitive information in the future.",
            "severity": "Medium", # Downgraded as it's empty
            "remediation": "Disable public access to debug.log (e.g., via .htaccess or server configuration). Ensure WP_DEBUG_LOG is false on production sites, or if used, that the log path is not web-accessible."
        })
        
    if findings["phpinfo_check"]["exposed_path"]:
        details_summary.append(f"CRITICAL: phpinfo() output exposed at {findings['phpinfo_check']['exposed_path']}.")
        state.add_remediation_suggestion("phpinfo_exposed", {
            "source": "WP Analyzer (Config Audit)",
            "description": f"A file exposing phpinfo() output was found at {findings['phpinfo_check']['exposed_path']}. This reveals extensive details about the PHP environment, server configuration, and potentially sensitive paths or variables.",
            "severity": "Critical",
            "remediation": "Immediately remove the file exposing phpinfo() output. Such files should only be used for temporary debugging and never left on a live server."
        })

    if findings["force_ssl_admin_check"]["likely_true"] is True:
        details_summary.append("FORCE_SSL_ADMIN is likely true or server enforces HTTPS for admin.")
        state.add_remediation_suggestion("force_ssl_admin_true", {
            "source": "WP Analyzer (Config Audit)",
            "description": "Access to wp-admin over HTTP appears to redirect to HTTPS, suggesting FORCE_SSL_ADMIN is active or server-level HTTPS enforcement is in place for the admin area.",
            "severity": "Info",
            "remediation": "This is a good security practice. Ensure your SSL/TLS certificate is valid and properly configured."
        })
    elif findings["force_ssl_admin_check"]["likely_true"] is False and parsed_target.scheme == "http":
         details_summary.append("FORCE_SSL_ADMIN is likely false on an HTTP site.")
         state.add_remediation_suggestion("force_ssl_admin_false", {
            "source": "WP Analyzer (Config Audit)",
            "description": "The site is served over HTTP, and access to wp-admin also appears to be over HTTP without forced redirection to HTTPS. This means admin credentials and session cookies could be transmitted insecurely.",
            "severity": "Medium",
            "remediation": "Set define('FORCE_SSL_ADMIN', true); in wp-config.php if an SSL certificate is available for the domain. Ideally, migrate the entire site to HTTPS."
        })

    # Add the informational messages for non-testable items
    state.add_remediation_suggestion("db_prefix_info", {
        "source": "WP Analyzer (Config Audit)", "description": findings["db_prefix_check"]["message"],
        "severity": "Info", "remediation": "Using a non-default database table prefix (i.e., not 'wp_') is a good security hardening step. This can be set during WordPress installation or changed later with plugins (requires caution and backups)."
    })
    # ... (similar for security_keys, file_permissions, htaccess_rules)


    if not details_summary:
        findings["details"] = "Configuration audit completed. No specific remote vulnerabilities detected by heuristics. Review informational checks."
    else:
        findings["details"] = "Configuration audit heuristics completed: " + " ".join(details_summary)
    
    findings["status"] = "Completed"
    all_wp_analyzer_findings = state.get_module_findings(module_key, {}) # Re-fetch
    all_wp_analyzer_findings[findings_key] = findings
    state.update_module_findings(module_key, all_wp_analyzer_findings)
    print(f"    [+] WordPress Configuration Audit (Remote Heuristics) finished.")
