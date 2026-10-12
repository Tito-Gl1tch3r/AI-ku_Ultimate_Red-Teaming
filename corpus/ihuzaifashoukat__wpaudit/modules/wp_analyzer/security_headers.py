import requests
import re
from urllib.parse import urljoin
from .utils import make_request
from core.utils import sanitize_filename # Corrected import

# --- Global Configuration for Security Headers ---
SECURITY_HEADER_CONFIG = {
    "Content-Security-Policy": {
        "present": True, "severity": "High", 
        "remediation": "Implement a strong Content Security Policy (CSP) to mitigate XSS and data injection attacks. Start with default-src 'self'; script-src 'self' 'nonce-XYZ' 'strict-dynamic'; object-src 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests; and expand as needed. Consider 'require-trusted-types-for \"script\"' for advanced protection. Ensure a reporting mechanism ('report-uri' or 'report-to') is configured.",
        "check_func": "_check_csp_details" # Placeholder, will be the actual function object
    },
    "Strict-Transport-Security": {
        "present": True, "severity": "Medium", 
        "remediation": "Implement HTTP Strict Transport Security (HSTS) to enforce HTTPS. A common policy is 'max-age=31536000; includeSubDomains; preload'. Consider submitting your site to the HSTS preload list.",
        "check_func": "_check_hsts_details" # Placeholder
    },
    "X-Content-Type-Options": {
        "present": True, "value_exact": "nosniff", "severity": "Low", 
        "remediation": "Set X-Content-Type-Options to 'nosniff' to prevent browsers from MIME-sniffing a response away from the declared content-type."
    },
    "X-Frame-Options": {
        "present": True, "value_in_exact": ["DENY", "SAMEORIGIN"], "severity": "Medium", 
        "remediation": "Set X-Frame-Options to 'DENY' or 'SAMEORIGIN' to protect against clickjacking. CSP 'frame-ancestors' is a more modern and flexible alternative; if 'frame-ancestors' is strongly configured, X-Frame-Options may be redundant but doesn't hurt as a fallback."
    },
    "Referrer-Policy": {
        "present": True, 
        "value_in_exact": ["no-referrer", "no-referrer-when-downgrade", "origin", "origin-when-cross-origin", "same-origin", "strict-origin", "strict-origin-when-cross-origin", "unsafe-url"], 
        "severity": "Low", 
        "remediation": "Set a Referrer-Policy (e.g., 'strict-origin-when-cross-origin' or 'no-referrer') to control how much referrer information is sent with requests."
    },
    "Permissions-Policy": { # Formerly Feature-Policy
        "present": True, "severity": "Low", 
        "remediation": "Implement Permissions-Policy to control access to browser features. Example: 'geolocation=(), microphone=(), camera=(), usb=(), payment=()'. Define a restrictive default policy if possible."
    },
    "X-XSS-Protection": { # Modern best practice is to disable and rely on CSP
        "present": False, "value_exact": "0", "severity": "Info", 
        "remediation": "Modern browsers recommend disabling X-XSS-Protection (set to '0') and relying on a strong Content Security Policy. If set to '1' or '1; mode=block', it's an older protection that might have bypasses or introduce self-XSS issues."
    },
    "Cross-Origin-Opener-Policy": { # COOP
        "present": True, "value_in_exact": ["same-origin", "same-origin-allow-popups", "unsafe-none"], "severity": "Medium", 
        "remediation": "Set Cross-Origin-Opener-Policy (COOP) to 'same-origin' or 'same-origin-allow-popups' to protect against cross-origin attacks like Spectre. 'unsafe-none' is the default and less secure."
    },
    "Cross-Origin-Embedder-Policy": { # COEP
        "present": True, "value_in_exact": ["require-corp", "credentialless", "unsafe-none"], "severity": "Medium", 
        "remediation": "Set Cross-Origin-Embedder-Policy (COEP) (e.g., 'require-corp' or 'credentialless') to enable cross-origin isolation and protect against Spectre-like attacks. This requires resources to opt-in via CORP or CORS."
    },
    "Cross-Origin-Resource-Policy": { # CORP
        "present": True, "value_in_exact": ["same-origin", "same-site", "cross-origin"], "severity": "Low", 
        "remediation": "Set Cross-Origin-Resource-Policy (CORP) (e.g., 'same-origin' or 'same-site') to control which cross-origin sites can embed your resources, protecting against Spectre and other attacks."
    },
    "Clear-Site-Data": {
        "present": False, "severity": "Info", # Optional, context-dependent
        "remediation": "Consider using the 'Clear-Site-Data' header (e.g., '\"cache\", \"cookies\", \"storage\", \"executionContexts\"') on logout or sensitive operations to clear browsing data and improve user privacy."
    },
    "NEL": { # Network Error Logging
        "present": False, "severity": "Info", # Optional, for monitoring
        "remediation": "Implement Network Error Logging (NEL) by setting the 'NEL' header with a JSON policy (e.g., {\"report_to\":\"default\",\"max_age\":2592000,\"include_subdomains\":true}) and a 'Reporting-Endpoints' header. This helps monitor network reliability issues."
    },
    "Reporting-Endpoints": { # Used with NEL, CSP report-to, Expect-CT
        "present": False, "severity": "Info", # Optional, for monitoring
        "remediation": "Define reporting endpoints using the 'Reporting-Endpoints' header (e.g., default=\"https://your-report-collector.example/default-endpoint\", csp-reports=\"https://your-report-collector.example/csp\") to collect reports from NEL, CSP, etc."
    },
    "Expect-CT": { # Certificate Transparency (being deprecated)
        "present": False, "severity": "Info", # Optional, and being deprecated
        "remediation": "The 'Expect-CT' header for Certificate Transparency is being deprecated. If previously used, ensure it's managed. Modern CT enforcement relies on browser mechanisms and SCTs embedded in certificates."
    },
    "Cache-Control": {
        "present": True, "severity": "Medium",
        "remediation": "Ensure 'Cache-Control' header is present and appropriately configured (e.g., 'no-store, no-cache, must-revalidate, private' for sensitive content; 'public, max-age=...' for static assets). Misconfiguration can lead to sensitive data leakage or stale content. Also consider 'Vary' header for dynamic content.",
        "check_func": "_check_cache_control_details" # Placeholder
    },
    "Pragma": { # HTTP/1.0 compatibility for no-cache
        "present": False, "value_exact": "no-cache", "severity": "Info",
        "remediation": "For HTTP/1.0 compatibility, 'Pragma: no-cache' can be used alongside 'Cache-Control: no-cache'. 'Cache-Control' is the primary mechanism for HTTP/1.1+."
    },
    "Expires": { # Legacy caching header
        "present": False, "severity": "Info",
        "remediation": "The 'Expires' header is a legacy caching mechanism. 'Cache-Control' is preferred. If used for non-caching, it should be set to a date in the past or '0'."
    }
}

# CSP Parser Helper (Simplified)
def _parse_csp(csp_header_value):
    directives = {}
    if not csp_header_value:
        return directives
    parts = csp_header_value.split(';')
    for part in parts:
        part = part.strip()
        if not part:
            continue
        directive_parts = part.split(None, 1) # Split only on the first space
        directive_name = directive_parts[0].lower()
        values = directive_parts[1].split() if len(directive_parts) > 1 else []
        directives[directive_name] = values
    return directives

# --- Specific Header Check Functions ---

def _check_cache_control_details(header_name, header_value, state, url_label, url_to_check):
    """Analyzes Cache-Control, Pragma, and Expires headers."""
    issues = []
    directives = [d.strip().lower() for d in header_value.split(',')]

    # Check for directives that prevent caching, good for sensitive data
    no_store = "no-store" in directives
    no_cache = "no-cache" in directives
    must_revalidate = "must-revalidate" in directives
    
    # Check for directives that allow caching, good for public static assets
    public = "public" in directives
    private = "private" in directives
    max_age_match = re.search(r"max-age=(\d+)", header_value, re.IGNORECASE)
    s_maxage_match = re.search(r"s-maxage=(\d+)", header_value, re.IGNORECASE)

    if no_store and public:
        issues.append({"header": header_name, "value": header_value, "expected": "Consistent caching strategy", "details": "Cache-Control contains conflicting 'no-store' and 'public' directives."})
    if no_cache and public and not max_age_match: # public with no-cache usually means revalidate
        issues.append({"header": header_name, "value": header_value, "expected": "Clear caching strategy", "details": "Cache-Control contains 'public' and 'no-cache' which can be ambiguous without max-age for revalidation. Consider if this is intended."})

    if url_label == "Login Page" or "admin" in url_to_check.lower(): # Heuristic for sensitive pages
        if not (no_store or no_cache):
            issues.append({"header": header_name, "value": header_value, "expected": "'no-store' or 'no-cache' for sensitive pages", "details": f"Sensitive page ({url_label}) should ideally have 'no-store' or 'no-cache' in Cache-Control."})
    elif not (public or private or no_store or no_cache):
         issues.append({"header": header_name, "value": header_value, "expected": "Explicit caching policy (public, private, no-store, or no-cache)", "details": "Cache-Control lacks explicit caching policy like 'public', 'private', 'no-store', or 'no-cache'."})

    # Check Pragma: no-cache (only relevant if Cache-Control is also not restrictive)
    # This check is now implicitly handled by SECURITY_HEADER_CONFIG for Pragma itself.
    # We can add an informational note if Pragma is used correctly.
    # headers = state.get_temp_data("current_headers_for_analysis", {}) # Requires passing headers or fetching again
    # pragma_header = headers.get("Pragma", "")
    # if "no-cache" in pragma_header.lower() and not (no_store or no_cache):
    #     print(f"        [i] {url_label}: Pragma: no-cache present, but Cache-Control is not similarly restrictive.")


    # Check Expires (only relevant if Cache-Control is not restrictive)
    # This is now handled by the main loop checking SECURITY_HEADER_CONFIG["Expires"]
    return issues

def _check_csp_details(header_name, header_value, state, url_label, url_to_check):
    issues = []
    parsed_csp = _parse_csp(header_value)
    if not parsed_csp:
        issues.append({"header": header_name, "value": header_value, "expected": "Parseable CSP", "details": "CSP header found but could not be parsed or is empty."})
        return issues

    # Check for unsafe directives
    unsafe_inline_script = "'unsafe-inline'" in parsed_csp.get("script-src", [])
    unsafe_inline_style = "'unsafe-inline'" in parsed_csp.get("style-src", [])
    unsafe_inline_default_script = "'unsafe-inline'" in parsed_csp.get("default-src", []) and not parsed_csp.get("script-src")
    unsafe_inline_default_style = "'unsafe-inline'" in parsed_csp.get("default-src", []) and not parsed_csp.get("style-src")
    
    if unsafe_inline_script or unsafe_inline_default_script:
        issues.append({"header": header_name, "value": header_value, "expected": "No 'unsafe-inline' for script-src (use nonces/hashes or 'strict-dynamic')", "details": "CSP allows 'unsafe-inline' for scripts, significantly increasing XSS risk."})
    if unsafe_inline_style or unsafe_inline_default_style:
         # Style 'unsafe-inline' is common but still a risk if user can inject styles.
        issues.append({"header": header_name, "value": header_value, "expected": "Consider avoiding 'unsafe-inline' for style-src if possible", "details": "CSP allows 'unsafe-inline' for styles. While common, it can be a risk if style injection is possible."})

    unsafe_eval_script = "'unsafe-eval'" in parsed_csp.get("script-src", [])
    unsafe_eval_default = "'unsafe-eval'" in parsed_csp.get("default-src", []) and not parsed_csp.get("script-src")
    if unsafe_eval_script or unsafe_eval_default:
        issues.append({"header": header_name, "value": header_value, "expected": "No 'unsafe-eval' for script-src", "details": "CSP allows 'unsafe-eval' for scripts, increasing XSS risk from eval-like functions."})

    # Check for overly broad sources
    broad_sources = ["*", "data:", "blob:", "filesystem:"] # data: for img-src is sometimes acceptable
    for directive in ["default-src", "script-src", "style-src", "img-src", "connect-src", "font-src", "media-src", "frame-src", "worker-src", "manifest-src"]:
        sources = parsed_csp.get(directive, [])
        for broad_src in broad_sources:
            if broad_src in sources:
                if not (directive == "img-src" and broad_src == "data:"): # Allow data: for img-src
                    issues.append({"header": header_name, "value": header_value, "expected": f"Specific, trusted sources for '{directive}'", "details": f"CSP directive '{directive}' uses overly broad source '{broad_src}', potentially allowing unintended resource loading."})
    
    # Check for missing essential directives
    if not parsed_csp.get("default-src"):
        issues.append({"header": header_name, "value": header_value, "expected": "Presence of 'default-src'", "details": "CSP missing 'default-src' directive. This is crucial as a fallback for unspecified directives."})
    
    object_src_values = parsed_csp.get("object-src", parsed_csp.get("default-src", [])) # Fallback to default-src if object-src not present
    if "'none'" not in object_src_values and object_src_values: # If object_src_values is empty, default-src might be 'none' or restrictive.
         # Check if default-src is restrictive enough if object-src is missing
        if not ("object-src" in parsed_csp or (parsed_csp.get("default-src") and "'none'" in parsed_csp.get("default-src"))):
            issues.append({"header": header_name, "value": header_value, "expected": "object-src 'none'", "details": "CSP 'object-src' should ideally be 'none' to prevent execution of plugins like Flash. If not set, ensure 'default-src' is restrictive."})

    base_uri_values = parsed_csp.get("base-uri", [])
    if not any(s in ["'self'", "'none'"] for s in base_uri_values) and base_uri_values:
         # If base-uri is missing, it's a weakness. If present but not 'self' or 'none', also a weakness.
        if "base-uri" not in parsed_csp:
             issues.append({"header": header_name, "value": header_value, "expected": "base-uri 'self' or 'none'", "details": "CSP 'base-uri' directive is missing. Risk of base tag hijacking."})
        else:
            issues.append({"header": header_name, "value": header_value, "expected": "base-uri 'self' or 'none'", "details": "CSP 'base-uri' is not set to 'self' or 'none', increasing risk of base tag hijacking."})

    form_action_values = parsed_csp.get("form-action", parsed_csp.get("default-src", []))
    if not any(s in ["'self'"] for s in form_action_values) and not parsed_csp.get("form-action"): # Check if form-action is explicitly set
         # If form-action is missing and default-src is not 'self' or more restrictive
        if not (parsed_csp.get("default-src") and any(s in ["'self'", "'none'"] for s in parsed_csp.get("default-src"))):
            issues.append({"header": header_name, "value": header_value, "expected": "form-action 'self' (or more restrictive)", "details": "CSP 'form-action' is not defined or too permissive. This restricts where forms can submit data."})
    
    # Clickjacking protection: frame-ancestors
    frame_ancestors_present = "frame-ancestors" in parsed_csp
    if not frame_ancestors_present:
        issues.append({"header": header_name, "value": header_value, "expected": "frame-ancestors directive", "details": "CSP missing 'frame-ancestors' directive for clickjacking protection. If X-Frame-Options is used, this might be acceptable, but 'frame-ancestors' is preferred."})
    else:
        if not any(s in ["'self'", "'none'"] for s in parsed_csp["frame-ancestors"]):
             issues.append({"header": header_name, "value": header_value, "expected": "frame-ancestors 'self' or 'none'", "details": "CSP 'frame-ancestors' is present but not set to 'self' or 'none', potentially allowing framing from unintended origins."})

    # Upgrade Insecure Requests
    if "upgrade-insecure-requests" not in parsed_csp:
        issues.append({"header": header_name, "value": header_value, "expected": "upgrade-insecure-requests directive", "details": "CSP missing 'upgrade-insecure-requests' directive. This helps ensure resources are loaded over HTTPS."})

    # Trusted Types
    if "require-trusted-types-for" not in parsed_csp or "'script'" not in parsed_csp.get("require-trusted-types-for", []):
        # This is an advanced feature, so maybe lower severity or informational
        print(f"        [i] CSP on {url_label} does not enforce 'require-trusted-types-for \"script\"'. This is an advanced XSS protection.")
    
    # Reporting
    if "report-uri" not in parsed_csp and "report-to" not in parsed_csp:
        issues.append({"header": header_name, "value": header_value, "expected": "report-uri or report-to directive", "details": "CSP missing 'report-uri' or 'report-to' directive for violation reporting. Reporting helps monitor and refine the policy."})
    
    return issues

def _check_hsts_details(header_name, header_value, state, url_label, url_to_check):
    issues = []
    max_age_match = re.search(r"max-age=(\d+)", header_value, re.IGNORECASE)
    # OWASP recommends at least 6 months (15768000 seconds), common practice is 1-2 years.
    # Let's use 6 months as minimum, 1 year (31536000) as recommended.
    min_recommended_max_age = 15552000 # ~6 months (as before)
    ideal_max_age = 31536000 # 1 year

    if max_age_match:
        max_age = int(max_age_match.group(1))
        if max_age < min_recommended_max_age:
            issues.append({"header": header_name, "value": header_value, "expected": f"max-age >= {min_recommended_max_age} (ideally >= {ideal_max_age})", "details": f"HSTS max-age ({max_age}) is less than the recommended minimum of {min_recommended_max_age} seconds. Consider setting to at least {ideal_max_age} (1 year)." })
        elif max_age < ideal_max_age:
             print(f"        [i] HSTS max-age on {url_label} is {max_age}s. This is acceptable, but {ideal_max_age}s (1 year) or more is common for established sites.")
    else:
        issues.append({"header": header_name, "value": header_value, "expected": "max-age directive", "details": "HSTS header missing 'max-age' directive."})
    
    if "includesubdomains" not in header_value.lower():
        issues.append({"header": header_name, "value": header_value, "expected": "includeSubDomains directive", "details": "HSTS header missing 'includeSubDomains' directive. This is crucial for protecting all subdomains."})
    
    if "preload" not in header_value.lower():
        # This is a recommendation, not strictly a misconfiguration if absent
        print(f"        [i] HSTS on {url_label} does not include 'preload'. Consider adding 'preload' and submitting to hstspreload.org for maximum protection.")
    else:
        print(f"        [+] HSTS 'preload' directive found on {url_label} (excellent practice). Ensure site meets preload list requirements.")
    return issues

def _analyze_headers_for_url(url_to_check, state, config, url_label="Target URL"):
    """Analyzes security headers for a specific URL using SECURITY_HEADER_CONFIG."""
    print(f"      Fetching headers from: {url_to_check} ({url_label})")
    response = make_request(url_to_check, config, method="HEAD", timeout=7)
    
    current_url_findings = {
        "url_checked": url_to_check,
        "status": "Error (Request Failed)", # Default status
        "headers_present": {},
        "missing_recommended": [],
        "misconfigured": [],
        "info_leak_headers": {}
    }

    if not response:
        return current_url_findings

    headers = response.headers # CaseInsensitiveDict
    current_url_findings["status"] = "Checked"
    
    # Iterate through the global SECURITY_HEADER_CONFIG
    for header_name, check_details in SECURITY_HEADER_CONFIG.items():
        header_value = headers.get(header_name)
        # Normalize header_value to empty string if None for consistent handling
        header_value_normalized = header_value if header_value is not None else ""
        current_url_findings["headers_present"][header_name] = header_value if header_value else "Not Present"

        # Check if a header expected to be present is missing
        if check_details.get("present") and not header_value:
            current_url_findings["missing_recommended"].append(header_name)
        
        # If header is present, perform value checks
        elif header_value:
            expected_value_exact = check_details.get("value_exact")
            if expected_value_exact and header_value_normalized.lower().strip() != expected_value_exact.lower():
                # Special handling for X-XSS-Protection: if it's expected to be absent OR '0',
                # then any other value is a misconfiguration.
                # If "present" is False, it means it should ideally not be there, or be '0'.
                # If it IS present, and not '0', it's a misconfiguration according to modern standards.
                if not (header_name == "X-XSS-Protection" and not check_details.get("present")):
                    current_url_findings["misconfigured"].append({
                        "header": header_name, 
                        "value": header_value, 
                        "expected": f"Exactly '{expected_value_exact}'", 
                        "details": "Value does not match recommended."
                    })

            expected_values_in_exact = check_details.get("value_in_exact")
            if expected_values_in_exact and header_value_normalized.lower().strip() not in [v.lower() for v in expected_values_in_exact]:
                current_url_findings["misconfigured"].append({
                    "header": header_name, 
                    "value": header_value, 
                    "expected": f"One of {expected_values_in_exact}", 
                    "details": "Value not in recommended set."
                })
            
            # Custom check function logic
            check_func_name = check_details.get("check_func")
            if check_func_name and isinstance(check_func_name, str): # Ensure it's a string placeholder first
                # The actual function mapping will happen before analyze_security_headers
                # For now, we assume it will be replaced by the actual function object later
                # If it's already a function (after mapping), call it
                pass # This logic will be handled when check_func is an actual function
            elif callable(check_func_name): # If it's already a function object
                 custom_issues = check_func_name(header_name, header_value, state, url_label, url_to_check)
                 current_url_findings["misconfigured"].extend(custom_issues)

        # Check if a header expected to be absent (or a specific value like '0') is present with a different value
        elif not check_details.get("present") and header_value:
            # Example: X-XSS-Protection should be absent or '0'. If it's present and not '0', it's a finding.
            expected_value_exact = check_details.get("value_exact") # e.g. '0' for X-XSS-Protection
            if expected_value_exact and header_value_normalized.lower().strip() != expected_value_exact.lower():
                current_url_findings["misconfigured"].append({
                    "header": header_name, 
                    "value": header_value, 
                    "expected": f"'{expected_value_exact}' or not present", 
                    "details": f"{header_name} is present with a non-recommended value. Modern best practice is often to disable (e.g., set to '{expected_value_exact}') or remove it."
                })
            elif not expected_value_exact: # If no specific value is expected when absent, any presence is notable if "present" is False
                 current_url_findings["misconfigured"].append({
                    "header": header_name, 
                    "value": header_value, 
                    "expected": "Not present", 
                    "details": f"{header_name} is present but is recommended to be absent for optimal security/modern practices."
                })


    # Information Leakage Headers
    for leak_header in ["Server", "X-Powered-By", "X-AspNet-Version", "X-AspNetMvc-Version"]:
        val = headers.get(leak_header)
        if val:
            current_url_findings["info_leak_headers"][leak_header] = val
            print(f"        [i] Info Leak: {leak_header}: {val} on {url_label}")
            # Remediation added globally later

    return current_url_findings

def _check_hsts_details(header_name, header_value, state, url_label, url_to_check): # Ensure this matches the 5-arg call if it's used by _analyze_headers_for_url
    issues = []
    max_age_match = re.search(r"max-age=(\d+)", header_value, re.IGNORECASE)
    min_recommended_max_age = 15552000 # ~6 months
    if max_age_match:
        max_age = int(max_age_match.group(1))
        if max_age < min_recommended_max_age:
            issues.append({"header": header_name, "value": header_value, "expected": f"max-age >= {min_recommended_max_age}", "details": f"HSTS max-age ({max_age}) is less than recommended {min_recommended_max_age} seconds."})
    else:
        issues.append({"header": header_name, "value": header_value, "expected": "max-age directive", "details": "HSTS header missing 'max-age' directive."})
    
    if "includesubdomains" not in header_value.lower(): issues.append({"header": header_name, "value": header_value, "expected": "includeSubDomains directive", "details": "HSTS header missing 'includeSubDomains' directive."})
    if "preload" in header_value.lower():
        print(f"        [+] HSTS 'preload' directive found on {url_label} (excellent practice). Ensure site meets preload list requirements.")
    return issues

# --- Main Analysis Function ---

# Helper to map function names (strings) in SECURITY_HEADER_CONFIG to actual function objects
# This should be called once after all _check_... functions are defined.
def _map_check_functions():
    function_map = {
        "_check_csp_details": _check_csp_details,
        "_check_hsts_details": _check_hsts_details,
        "_check_cache_control_details": _check_cache_control_details
        # Add other check functions here if they are introduced
    }
    for header, config in SECURITY_HEADER_CONFIG.items():
        if "check_func" in config and isinstance(config["check_func"], str):
            func_name = config["check_func"]
            if func_name in function_map:
                config["check_func"] = function_map[func_name]
            else:
                print(f"[!] Warning: Check function '{func_name}' for header '{header}' not found in function_map. Will not be called.")
                config["check_func"] = None # Or remove, or handle error

_map_check_functions() # Call it once at module load time after functions are defined.


def analyze_security_headers(state, config, target_url):
    """Analyzes the security headers of the target URL and wp-login.php."""
    wp_analyzer_module_key = "wp_analyzer" # The main key for all wp_analyzer findings
    findings_subkey = "security_headers" # Align with the key used in analyzer.py's default_analyzer_findings

    # Get the entire wp_analyzer findings dictionary
    analyzer_findings = state.get_module_findings(wp_analyzer_module_key, {})
    
    # Get or initialize the specific findings for security headers
    current_phase_findings = analyzer_findings.get(findings_subkey, {})
    if not current_phase_findings: # Initialize if not present
        current_phase_findings = {
            "status": "Running",
            "details_summary": "Analyzing security headers...",
            "target_url_analysis": {},
            "login_page_analysis": {}
        }
    current_phase_findings["status"] = "Running" # Ensure status is running
    analyzer_findings[findings_subkey] = current_phase_findings # Put it back into the main dict

    print("    [i] Enhanced Security Header Analysis...")

    # Analyze main target URL
    # _analyze_headers_for_url now needs to be aware it's part of a larger structure or state is passed for remediation
    current_phase_findings["target_url_analysis"] = _analyze_headers_for_url(target_url, state, config, "Target URL")

    # Analyze wp-login.php
    login_url = urljoin(target_url, "wp-login.php")
    # Check if login page is accessible before analyzing its headers
    # Access the broader wp_analyzer findings to get login_page_analysis results
    login_page_info = analyzer_findings.get("login_page_analysis", {}) # Assuming login_page_analysis is another subkey
    
    if login_page_info.get("standard_login_accessible") is True or login_page_info.get("final_login_page_url"):
        effective_login_url = login_page_info.get("final_login_page_url", login_url)
        current_phase_findings["login_page_analysis"] = _analyze_headers_for_url(effective_login_url, state, config, "Login Page")
    else:
        print(f"      Skipping header analysis for login page as it was not found accessible by login_page analysis.")
        current_phase_findings["login_page_analysis"] = {"url_checked": login_url, "status": "Skipped (Login Page Not Accessible)", "headers_present": {}}

    # Consolidate and add global remediations based on target_url_analysis
    target_analysis = current_phase_findings["target_url_analysis"]
    if target_analysis.get("status") == "Checked":
        for header_name in target_analysis.get("missing_recommended", []):
            # Use SECURITY_HEADER_CONFIG for remediation details
            check_def = SECURITY_HEADER_CONFIG.get(header_name, {})
            state.add_remediation_suggestion(f"sec_header_missing_{sanitize_filename(header_name.lower())}", {
                "source": "WP Analyzer (Security Headers)", 
                "description": f"Recommended security header '{header_name}' is missing from the main site response.", 
                "severity": check_def.get("severity", "Low"), # Default severity if not in config
                "remediation": check_def.get("remediation", "Implement this security header according to best practices.")
            })
        for misconfig in target_analysis.get("misconfigured", []):
            header_name = misconfig["header"]
            # Use SECURITY_HEADER_CONFIG for remediation details
            check_def = SECURITY_HEADER_CONFIG.get(header_name, {})
            state.add_remediation_suggestion(f"sec_header_misconfigured_{sanitize_filename(header_name.lower())}", {
                "source": "WP Analyzer (Security Headers)", 
                "description": f"Security header '{header_name}' is present but potentially misconfigured. Value: '{misconfig['value']}'. Expected: '{misconfig['expected']}'. Details: {misconfig.get('details', '')}",
                "severity": check_def.get("severity", "Low"), # Default severity
                "remediation": check_def.get("remediation", f"Review and correct the configuration of the '{header_name}' header.")
            })
        for leak_header, val in target_analysis.get("info_leak_headers", {}).items():
            # Remediation for info leak headers is generic, not in SECURITY_HEADER_CONFIG's main structure
            state.add_remediation_suggestion(f"sec_header_info_leak_{sanitize_filename(leak_header.lower())}", {
                "source": "WP Analyzer (Security Headers)", 
                "description": f"Informational header '{leak_header}: {val}' found, potentially revealing server/technology details.",
                "severity": "Low", 
                "remediation": f"Consider removing or obscuring the '{leak_header}' header via server configuration to reduce information leakage."
            })
        
        num_missing = len(target_analysis.get("missing_recommended", []))
        num_misconfigured = len(target_analysis.get("misconfigured", []))
        if num_missing == 0 and num_misconfigured == 0:
            current_phase_findings["details_summary"] = "Essential security headers on target URL appear to be present and reasonably configured."
        else:
            current_phase_findings["details_summary"] = f"Target URL: {num_missing} recommended headers missing, {num_misconfigured} potentially misconfigured."
            if num_missing > 0: state.add_summary_point(f"Missing {num_missing} security headers on main target.")
    else: # Error fetching target URL headers
        current_phase_findings["details_summary"] = f"Could not analyze security headers for target URL: {target_analysis.get('status')}"

    current_phase_findings["status"] = "Completed"
    # Update the main analyzer_findings dict with the changes for this sub-module
    analyzer_findings[findings_subkey] = current_phase_findings
    # Save the entire updated wp_analyzer findings back to the state
    state.update_module_findings(wp_analyzer_module_key, analyzer_findings)
    
    print(f"    [+] Enhanced Security Header analysis finished. Summary: {current_phase_findings['details_summary']}")
