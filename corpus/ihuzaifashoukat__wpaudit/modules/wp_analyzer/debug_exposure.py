import re
import time
from urllib.parse import urljoin
from core.utils import sanitize_filename # Core utils needed here
from .utils import make_request # Local utils for requests

def check_wp_debug_exposure(state, config, target_url):
    """Checks for signs of WP_DEBUG being enabled and exposing errors on pages."""
    module_key = "wp_analyzer"
    analyzer_findings = state.get_module_findings(module_key, {})
    # Ensure the specific key exists before trying to access sub-keys
    if "wp_debug_exposure" not in analyzer_findings:
        analyzer_findings["wp_debug_exposure"] = {"status": "Running", "exposed_on_pages": []}
    debug_exposure_details = analyzer_findings["wp_debug_exposure"]

    # Check config flag first
    if not config.get("analyzer_check_wp_debug", True):
        print("    [i] WP_DEBUG exposure check disabled in configuration.")
        debug_exposure_details["status"] = "Disabled in Config"
        analyzer_findings["wp_debug_exposure"] = debug_exposure_details
        state.update_module_findings(module_key, analyzer_findings)
        return # Exit if disabled

    # Common PHP error strings that might appear if WP_DEBUG is on and errors are displayed
    # Using raw strings (r"...") for regex patterns
    debug_error_patterns = [
        r"<b>Notice</b>:", r"<b>Warning</b>:", r"<b>Fatal error</b>:",
        r"<b>Parse error</b>:", r"<b>Deprecated</b>:",
        r"Call Stack", r"Stack trace",
        r"in\s+.+?\s+on\s+line\s+\d+", # Matches "in /path/to/file.php on line 123"
        r"WordPress\s+database\s+error" # Matches common WP DB error message
    ]
    # Compile patterns for efficiency
    compiled_patterns = [re.compile(p, re.IGNORECASE) for p in debug_error_patterns]

    # Pages to check (can be expanded based on findings from other modules)
    pages_to_check = [
        target_url, # Check homepage
        urljoin(target_url, "/wp-login.php"), # Check login page
        # Check a non-existent page which might trigger 404-related errors if debug is on
        urljoin(target_url, "/nonexistent-page-for-debug-test-" + sanitize_filename(str(time.time())) + ".php")
    ]
    # Future enhancement: Add paths discovered by directory bruteforcer or sitemap scanner

    # Ensure exposed_on_pages list exists
    if "exposed_on_pages" not in debug_exposure_details: # For PHP error messages
        debug_exposure_details["exposed_on_pages"] = []
    if "exposed_debug_log_url" not in debug_exposure_details: # For debug.log
        debug_exposure_details["exposed_debug_log_url"] = None
    if "query_monitor_footprints" not in debug_exposure_details: # For Query Monitor
        debug_exposure_details["query_monitor_footprints"] = {"detected_on_pages": [], "details": []}
    if "debug_bar_footprints" not in debug_exposure_details: # For Debug Bar
        debug_exposure_details["debug_bar_footprints"] = {"detected_on_pages": [], "details": []}
    if "kint_debugger_footprints" not in debug_exposure_details: # For Kint Debugger
        debug_exposure_details["kint_debugger_footprints"] = {"detected_on_pages": [], "details": []}
    if "phpinfo_exposure" not in debug_exposure_details: # For phpinfo()
        debug_exposure_details["phpinfo_exposure"] = {"exposed_paths": [], "details": ""}


    exposed_php_error_pages = debug_exposure_details["exposed_on_pages"]
    found_php_error_exposure = False

    print("    [i] Checking for PHP error message exposure (WP_DEBUG)...")
    for page_url in pages_to_check:
        print(f"      Checking for PHP errors on: {page_url}")
        try:
            response = make_request(page_url, config, method="GET", timeout=7)
            if response and response.text:
                page_found_php_error = False
                for pattern in compiled_patterns:
                    if pattern.search(response.text):
                        print(f"        [!!!] Potential PHP error (WP_DEBUG) exposure found on: {page_url}")
                        if page_url not in exposed_php_error_pages:
                            exposed_php_error_pages.append(page_url)
                        found_php_error_exposure = True
                        page_found_php_error = True
                        # Remediation suggestion added once later if found_php_error_exposure is true
                        break 
                # Query Monitor check on this page's content
                if config.get("analyzer_check_query_monitor", True):
                    qm_comments = re.findall(r"<!-- Query Monitor.*?-->|<!-- QM.*?-->", response.text, re.DOTALL)
                    qm_ids_classes = re.findall(r"id=['\"]query-monitor(-.+)?['\"]|class=['\"]qm(-.+)?['\"]", response.text)
                    if qm_comments or qm_ids_classes:
                        print(f"        [!] Query Monitor footprints detected on: {page_url}")
                        if page_url not in debug_exposure_details["query_monitor_footprints"]["detected_on_pages"]:
                            debug_exposure_details["query_monitor_footprints"]["detected_on_pages"].append(page_url)
                        if qm_comments and "Query Monitor HTML output" not in debug_exposure_details["query_monitor_footprints"]["details"]:
                             debug_exposure_details["query_monitor_footprints"]["details"].append("Query Monitor HTML output (comments) found.")
                        if qm_ids_classes and "Query Monitor CSS IDs/classes found." not in debug_exposure_details["query_monitor_footprints"]["details"]:
                             debug_exposure_details["query_monitor_footprints"]["details"].append("Query Monitor CSS IDs/classes found.")

                # Debug Bar check
                if config.get("analyzer_check_debug_bar", True):
                    db_comments = re.findall(r"<!-- Debug Bar -->", response.text, re.IGNORECASE)
                    db_ids_classes = re.findall(r"id=['\"]wp-admin-bar-debug-bar(-.+)?['\"]|class=['\"]debug-bar(-.+)?['\"]", response.text, re.IGNORECASE)
                    if db_comments or db_ids_classes:
                        print(f"        [!] Debug Bar footprints detected on: {page_url}")
                        if page_url not in debug_exposure_details["debug_bar_footprints"]["detected_on_pages"]:
                            debug_exposure_details["debug_bar_footprints"]["detected_on_pages"].append(page_url)
                        if db_comments and "Debug Bar HTML comments found." not in debug_exposure_details["debug_bar_footprints"]["details"]:
                             debug_exposure_details["debug_bar_footprints"]["details"].append("Debug Bar HTML comments found.")
                        if db_ids_classes and "Debug Bar CSS IDs/classes found." not in debug_exposure_details["debug_bar_footprints"]["details"]:
                             debug_exposure_details["debug_bar_footprints"]["details"].append("Debug Bar CSS IDs/classes found.")
                
                # Kint Debugger check
                if config.get("analyzer_check_kint_debugger", True):
                    kint_classes = re.findall(r"class=['\"]kint(\s|-)['\"]", response.text, re.IGNORECASE) # e.g. class="kint", class="kint-rich"
                    kint_output_markers = re.findall(r"<pre class=['\"]kint-source['\"]>|Kint::dump\(", response.text, re.IGNORECASE) # Basic Kint output structure
                    if kint_classes or kint_output_markers:
                        print(f"        [!] Kint Debugger footprints detected on: {page_url}")
                        if page_url not in debug_exposure_details["kint_debugger_footprints"]["detected_on_pages"]:
                            debug_exposure_details["kint_debugger_footprints"]["detected_on_pages"].append(page_url)
                        if kint_classes and "Kint Debugger CSS classes found." not in debug_exposure_details["kint_debugger_footprints"]["details"]:
                             debug_exposure_details["kint_debugger_footprints"]["details"].append("Kint Debugger CSS classes found.")
                        if kint_output_markers and "Kint Debugger output markers found." not in debug_exposure_details["kint_debugger_footprints"]["details"]:
                             debug_exposure_details["kint_debugger_footprints"]["details"].append("Kint Debugger output markers found.")

        except Exception as e:
            print(f"        [-] Error checking page {page_url} for debug exposure: {e}")

    debug_exposure_details["exposed_on_pages"] = exposed_php_error_pages
    if found_php_error_exposure:
        state.add_critical_alert(f"WP_DEBUG errors potentially exposed on one or more pages.")
        state.add_remediation_suggestion("wp_debug_php_errors_exposed", {
            "source": "WP Analyzer (Debug Exposure)",
            "description": f"PHP error messages (indicative of WP_DEBUG=true and display_errors=On) found on pages like: {', '.join(exposed_php_error_pages[:2])}{'...' if len(exposed_php_error_pages)>2 else ''}. This can leak sensitive information.",
            "severity": "Medium",
            "remediation": "Ensure WP_DEBUG and WP_DEBUG_DISPLAY are false on production. Log errors to a private file (WP_DEBUG_LOG true, but ensure log file is not web accessible)."
        })

    # Check for publicly accessible debug.log and other common log files
    if config.get("analyzer_check_debug_log_files", True):
        print("    [i] Checking for publicly accessible log files (debug.log, error_log)...")
        log_files_to_check = [
            "wp-content/debug.log",
            "debug.log", # Root directory
            "error_log", # Common PHP error log name in various locations
            "wp-admin/error_log",
            "wp-includes/error_log"
        ]
        found_public_log = False
        for log_file_path in log_files_to_check:
            log_url = urljoin(target_url, log_file_path)
            try:
                log_response = make_request(log_url, config, method="GET", timeout=7)
                if log_response and log_response.status_code == 200 and log_response.text:
                    # Check if it looks like a log file (e.g., contains timestamps, PHP errors, or just isn't tiny)
                    if re.search(r"\[\d{2,4}[-/][A-Za-z0-9]{2,3}[-/]\d{2,4}[\sT]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:[+-]\d{2}:\d{2}|Z| UTC)?\]|PHP (Fatal error|Warning|Notice|Parse error|Deprecated):", log_response.text, re.IGNORECASE) or len(log_response.text) > 200: # 200 bytes as a heuristic for non-empty
                        print(f"    [!!!] Publicly accessible log file found and contains data: {log_url}")
                        if log_file_path == "wp-content/debug.log": # Specific handling for the main debug.log
                            debug_exposure_details["exposed_debug_log_url"] = log_url
                        else: # Store other exposed logs
                            if "other_exposed_logs" not in debug_exposure_details:
                                debug_exposure_details["other_exposed_logs"] = []
                            if log_url not in debug_exposure_details["other_exposed_logs"]:
                                 debug_exposure_details["other_exposed_logs"].append(log_url)
                        found_public_log = True
                        state.add_critical_alert(f"Publicly accessible log file found: {log_url}")
                        state.add_remediation_suggestion(f"wp_log_exposed_{sanitize_filename(log_file_path)}", {
                            "source": "WP Analyzer (Debug Exposure)",
                            "description": f"A log file ({log_file_path}) is publicly accessible at {log_url} and may contain sensitive debug information.",
                            "severity": "High" if "debug.log" in log_file_path else "Medium",
                            "remediation": f"Ensure log files like '{log_file_path}' are not publicly web accessible (e.g., via .htaccess, server configuration, or by ensuring WP_DEBUG_LOG is false on production for debug.log). Delete old log files if not needed."
                        })
                    else:
                        print(f"      [?] {log_url} is accessible but doesn't appear to be a typical log file or is empty.")
                elif log_response and log_response.status_code != 404:
                     print(f"      [i] {log_url} returned status {log_response.status_code} (not 200 or 404).")
                # else: 404 or request failed, which is good in this context for logs
            except Exception as e:
                print(f"      [-] Error checking for log file {log_url}: {e}")
        if not found_public_log:
            print(f"      [+] No common publicly accessible log files (debug.log, error_log variants) found or requests failed.")
    else:
        print("    [i] Publicly accessible log file check disabled in configuration.")


    # Check for phpinfo() file exposure
    if config.get("analyzer_check_phpinfo", True):
        print("    [i] Checking for phpinfo() file exposure...")
        phpinfo_paths = ["phpinfo.php", "info.php", "test.php", "p.php", "i.php", "php.php"]
        found_phpinfo = False
        for p_path in phpinfo_paths:
            phpinfo_url = urljoin(target_url, p_path)
            try:
                response = make_request(phpinfo_url, config, method="GET", timeout=7)
                if response and response.status_code == 200 and response.text:
                    # A very basic check for phpinfo output. More robust checks are complex.
                    if "PHP Version" in response.text and "Configuration" in response.text and "phpinfo()" in response.text:
                        print(f"    [!!!] Potential phpinfo() exposure found at: {phpinfo_url}")
                        if phpinfo_url not in debug_exposure_details["phpinfo_exposure"]["exposed_paths"]:
                            debug_exposure_details["phpinfo_exposure"]["exposed_paths"].append(phpinfo_url)
                        found_phpinfo = True
            except Exception as e:
                print(f"      [-] Error checking {phpinfo_url} for phpinfo exposure: {e}")

        if found_phpinfo:
            debug_exposure_details["phpinfo_exposure"]["details"] = f"phpinfo() output detected on {len(debug_exposure_details['phpinfo_exposure']['exposed_paths'])} path(s)."
            state.add_critical_alert(f"Potential phpinfo() exposure detected.")
            state.add_remediation_suggestion("phpinfo_exposed", {
                "source": "WP Analyzer (Debug Exposure)",
                "description": f"A page exposing phpinfo() output was found at one or more locations (e.g., {debug_exposure_details['phpinfo_exposure']['exposed_paths'][0]}). This reveals detailed server and PHP configuration, which is a significant information leak.",
                "severity": "High",
                "remediation": "Remove any files that output phpinfo() from web-accessible locations on production servers. Such files should only be used temporarily for diagnostics and then deleted."
            })
        else:
            print(f"      [+] No common phpinfo() files found.")
    else:
        print("    [i] phpinfo() file exposure check disabled in configuration.")


    # Consolidate status
    final_details_parts = []
    if found_php_error_exposure:
        final_details_parts.append(f"PHP errors exposed on {len(exposed_php_error_pages)} page(s).")
    if debug_exposure_details["exposed_debug_log_url"]: # Specifically wp-content/debug.log
        final_details_parts.append("Public wp-content/debug.log found.")
    if debug_exposure_details.get("other_exposed_logs"):
        final_details_parts.append(f"{len(debug_exposure_details['other_exposed_logs'])} other public log file(s) found.")
    if debug_exposure_details["query_monitor_footprints"]["detected_on_pages"]:
        final_details_parts.append(f"Query Monitor footprints on {len(debug_exposure_details['query_monitor_footprints']['detected_on_pages'])} page(s).")
        state.add_remediation_suggestion("query_monitor_exposed", { # This remediation was already good
            "source": "WP Analyzer (Debug Exposure)",
            "description": f"Query Monitor plugin footprints detected. If its output is visible to unauthenticated users or on production, it can leak sensitive information.",
            "severity": "Low", # Can be higher if actual data is shown
            "remediation": "Ensure Query Monitor (or similar debugging plugins) are configured to only display output to authenticated administrators, or are disabled on production sites."
        })
    if debug_exposure_details["debug_bar_footprints"]["detected_on_pages"]:
        final_details_parts.append(f"Debug Bar footprints on {len(debug_exposure_details['debug_bar_footprints']['detected_on_pages'])} page(s).")
        state.add_remediation_suggestion("debug_bar_exposed", {
            "source": "WP Analyzer (Debug Exposure)",
            "description": f"Debug Bar plugin footprints detected. If its output is visible to unauthenticated users or on production, it can leak sensitive information.",
            "severity": "Low",
            "remediation": "Ensure Debug Bar (or similar debugging plugins) are configured to only display output to authenticated administrators, or are disabled on production sites."
        })
    if debug_exposure_details["kint_debugger_footprints"]["detected_on_pages"]:
        final_details_parts.append(f"Kint Debugger footprints on {len(debug_exposure_details['kint_debugger_footprints']['detected_on_pages'])} page(s).")
        state.add_remediation_suggestion("kint_debugger_exposed", {
            "source": "WP Analyzer (Debug Exposure)",
            "description": f"Kint Debugger plugin footprints detected. If its output is visible to unauthenticated users or on production, it can leak sensitive information.",
            "severity": "Medium", # Kint often dumps more verbose data
            "remediation": "Ensure Kint Debugger (or similar debugging plugins/code) are removed or disabled on production sites."
        })
    if debug_exposure_details["phpinfo_exposure"]["exposed_paths"]:
        final_details_parts.append(f"phpinfo() exposed on {len(debug_exposure_details['phpinfo_exposure']['exposed_paths'])} path(s).")
        # Remediation for phpinfo already added when found_phpinfo is true


    if not final_details_parts:
        debug_exposure_details["status"] = "Likely Not Exposed"
        print("    [+] No obvious signs of common debug information exposure found by these enhanced checks.")
    else:
        debug_exposure_details["status"] = "Potential Exposure Found"
    
    debug_exposure_details["details_summary"] = " ".join(final_details_parts) if final_details_parts else "No specific debug exposures identified by these checks."

    analyzer_findings["wp_debug_exposure"] = debug_exposure_details
    state.update_module_findings(module_key, analyzer_findings)
