import json
import re
from urllib.parse import urljoin, urlparse
from .utils import make_request # sanitize_filename is not used here, but if it were, it should be from core.utils
from core.utils import sanitize_filename # Example if it were needed

# Known core/common WordPress REST API namespaces to potentially exclude from "custom" or to analyze differently
CORE_COMMON_REST_NAMESPACES = [
    "wp/v2", "oembed/1.0", "wc/v1", "wc/v2", "wc/v3", "wc-blocks", "wc-store-api",
    "contact-form-7/v1", "jetpack/v4", "yoast/v1", "buddypress/v1", "regenerate-thumbnails/v1",
    "akismet/v1", "wordfence/v1", # Cleaned up jetpack/v4 duplicate
    "elementor/v1", # Elementor
    "wp-site-health/v1", # Site Health
    "yoast/v2", # Yoast SEO often adds multiple
    "wp/v2/block-renderer", # Common for block-based themes
    "wpstatistics/v2" # WP Statistics plugin
]

# Keywords for parameters that might be sensitive if accessible via GET unauthenticated in custom endpoints
SENSITIVE_PARAM_KEYWORDS = [
    'id', 'user_id', 'email', 'pass', 'token', 'key', 'secret', 'query', 'search', 's', # General
    'path', 'file', 'url', 'redirect', 'include', 'load', # File/Path related
    'filter', 'orderby', 'author', 'slug', # Data filtering/selection
    'action', 'cmd', 'exec' # Action/Command related
]


def analyze_rest_api_authenticated(state, config, target_url, findings_key="rest_api_analysis"):
    """
    Placeholder for authenticated REST API checks.
    This would involve using credentials from config to make authenticated requests.
    """
    module_key = "wp_analyzer"
    auth_findings = {
        "status": "Not Performed",
        "details": "Authenticated REST API checks require credentials in config and are not fully implemented in this scan.",
        "sensitive_settings_exposed": None,
        "user_management_caps": None,
        # Add more specific authenticated check results here
    }
    
    # Example: Check if config has API credentials
    # if config.get_value('wordpress.api_user') and config.get_value('wordpress.api_password'):
    #     print("    [i] Authenticated REST API checks would run here...")
    #     # auth_findings["status"] = "Running"
    #     # ... perform authenticated checks ...
    #     # auth_findings["status"] = "Completed"
    # else:
    #     print("    [i] Skipping authenticated REST API checks: Credentials not provided in config.")

    current_findings = state.get_specific_finding(module_key, findings_key)
    if current_findings:
        current_findings["authenticated_checks"] = auth_findings
        state.update_specific_finding(module_key, findings_key, current_findings)
    else: # Should not happen if called after general analysis
        state.add_finding(module_key, findings_key, {"authenticated_checks": auth_findings})


def analyze_rest_api_general(state, config, target_url):
    """
    Performs general analysis of the WordPress REST API.
    - Lists all namespaces and their routes.
    - Checks for information disclosure from the API root.
    - Checks accessibility of core endpoints (e.g., posts, users) unauthenticated.
    - Notes if REST API seems disabled or protected.
    """
    module_key = "wp_analyzer"
    # Use a more general key for these findings, distinct from just user enum
    findings_key = "rest_api_analysis"
    findings = state.get_specific_finding(module_key, findings_key, {
        "status": "Running",
        "details": "Performing general REST API analysis.",
        "api_root_url": None,
        "api_root_accessible": None, # True, False, "Error", "Protected"
        "api_root_status_code": None,
        "api_root_info_disclosure": {}, # Site name, description, auth methods etc.
        "api_root_cors_policy": None,
        "namespaces": [], 
        "custom_namespaces_identified": [],
        "custom_endpoint_analysis": [], # NEW: For results of sensitive param checks in custom EPs
        "core_endpoint_access": {
            "users": {"status": "Not Checked", "accessible_unauth": None, "data_preview": None, "exposed_user_details": []},
            "posts": {"status": "Not Checked", "accessible_unauth": None, "count_unauth": None, "exposes_author_info": False, "author_info_preview": []},
            "pages": {"status": "Not Checked", "accessible_unauth": None, "count_unauth": None, "exposes_author_info": False, "author_info_preview": []},
            "media": {"status": "Not Checked", "accessible_unauth": None, "count_unauth": None, "exposes_author_info": False, "author_info_preview": []},
            "settings": {"status": "Not Checked", "accessible_unauth": None, "data_preview": None},
            "categories": {"status": "Not Checked", "accessible_unauth": None, "count_unauth": None, "data_preview": None},
            "tags": {"status": "Not Checked", "accessible_unauth": None, "count_unauth": None, "data_preview": None}
        },
        "authenticated_checks": { # NEW Placeholder
             "status": "Not Performed", 
             "details": "Authenticated checks not run."
        }
    })
    print("    [i] Analyzing WordPress REST API General Security (Unauthenticated)...")

    wp_json_url = urljoin(target_url.rstrip('/'), "/wp-json/")
    findings["api_root_url"] = wp_json_url
    
    # 1. Check API Root (/wp-json/)
    print(f"      Checking REST API root: {wp_json_url}")
    try:
        response_root = make_request(wp_json_url, config, method="GET", timeout=10)
        if response_root:
            findings["api_root_status_code"] = response_root.status_code
            
            # CORS Check for API Root
            findings["api_root_cors_policy"] = response_root.headers.get("Access-Control-Allow-Origin")
            if findings["api_root_cors_policy"] == "*":
                print(f"        [!] REST API root has a permissive CORS policy: Access-Control-Allow-Origin: *")
                state.add_remediation_suggestion("rest_api_root_permissive_cors", {
                    "source": "WP Analyzer (REST API)",
                    "description": f"The REST API root ({wp_json_url}) has a permissive CORS policy (Access-Control-Allow-Origin: *). This could be a risk if the API relies on cookie-based authentication for sensitive operations accessible via GET requests from other origins.",
                    "severity": "Low",
                    "remediation": "Restrict the Access-Control-Allow-Origin header to only trusted domains or remove it if cross-origin API access is not required."
                })
            elif findings["api_root_cors_policy"]:
                print(f"        [i] REST API root CORS policy: Access-Control-Allow-Origin: {findings['api_root_cors_policy']}")

            if response_root.status_code == 200:
                findings["api_root_accessible"] = True
                print(f"        [+] REST API root accessible (Status: 200).")
                try:
                    data_root = response_root.json()
                    # Information disclosure from root
                    root_info = {
                        "name": data_root.get("name"), "description": data_root.get("description"),
                        "url": data_root.get("url"), "home": data_root.get("home"),
                        "gmt_offset": data_root.get("gmt_offset"), "timezone_string": data_root.get("timezone_string"),
                        "authentication_methods_raw": data_root.get("authentication"), # Can reveal auth methods
                        "namespaces_count": len(data_root.get("namespaces", []))
                    }
                    findings["api_root_info_disclosure"] = {k:v for k,v in root_info.items() if v is not None}
                    if root_info.get("name"): print(f"          Site Name (from API): {root_info['name']}")
                    if root_info.get("authentication_methods_raw"):
                        print(f"          Available Authentication Methods (from API root): {root_info['authentication_methods_raw']}")
                    
                    # Namespace and Route Listing
                    if "namespaces" in data_root and isinstance(data_root["namespaces"], list):
                        print(f"        Discovering all namespaces and their routes...")
                        for ns_name in data_root["namespaces"]:
                            is_core_common_ns = any(ns_name.startswith(core_ns_prefix) for core_ns_prefix in CORE_COMMON_REST_NAMESPACES)
                            ns_data = {"name": ns_name, "routes_url": None, "routes": [], "is_core_common": is_core_common_ns}
                            
                            if not is_core_common_ns:
                                if ns_name not in findings["custom_namespaces_identified"]:
                                    findings["custom_namespaces_identified"].append(ns_name)
                                print(f"          [i] Discovered custom/plugin namespace: {ns_name}")
                            
                            namespace_specific_url = data_root["_links"].get(f"https://api.w.org/namespace/{ns_name}", [{}])[0].get("href")
                            if not namespace_specific_url: # Fallback if not in _links (older WP?)
                                namespace_specific_url = urljoin(wp_json_url, ns_name)
                            
                            ns_data["routes_url"] = namespace_specific_url
                            try:
                                resp_ns = make_request(namespace_specific_url, config, method="GET", timeout=7)
                                if resp_ns and resp_ns.status_code == 200:
                                    ns_routes_data = resp_ns.json()
                                    if "routes" in ns_routes_data and isinstance(ns_routes_data["routes"], dict):
                                        for route_path, route_details_obj in ns_routes_data["routes"].items():
                                            # route_details_obj can be a dict or a list of endpoint dicts
                                            endpoints = route_details_obj.get("endpoints", []) if isinstance(route_details_obj, dict) else []
                                            if not endpoints and isinstance(route_details_obj, list): # Handle if route_details_obj is the list of endpoints
                                                endpoints = route_details_obj

                                            methods = []
                                            args_summary = {} # Collect args from first endpoint def
                                            for ep_detail in endpoints:
                                                methods.extend(ep_detail.get("methods", []))
                                                if not args_summary and ep_detail.get("args"): # Get args from first one
                                                    args_summary = {k:{"required":v.get("required", False)} for k,v in ep_detail.get("args", {}).items()}
                                            
                                            full_route_url = urljoin(namespace_specific_url + ('/' if not namespace_specific_url.endswith('/') else ''), route_path.lstrip('/'))
                                            ns_data["routes"].append({
                                                "path": route_path,
                                                "full_route_url": full_route_url, # NEW
                                                "methods": sorted(list(set(methods))),
                                                "args_summary": args_summary
                                            })
                                findings["namespaces"].append(ns_data)
                            except Exception as e_ns: print(f"          Error fetching/parsing namespace {ns_name}: {e_ns}")
                        print(f"        [+] Discovered {len(findings['namespaces'])} namespaces with their routes.")
                        if findings["custom_namespaces_identified"]:
                            print(f"          [*] Identified {len(findings['custom_namespaces_identified'])} custom/plugin namespaces: {', '.join(findings['custom_namespaces_identified'])}")
                            state.add_remediation_suggestion("rest_api_custom_namespaces_review", {
                                "source": "WP Analyzer (REST API)",
                                "description": f"Custom or plugin-specific REST API namespaces found: {', '.join(findings['custom_namespaces_identified'])}. These may expose additional functionality or data.",
                                "severity": "Info",
                                "remediation": "Review these custom REST API namespaces and their endpoints to ensure they do not expose sensitive information or unintended functionality, and that they implement proper access controls."
                            })

                except json.JSONDecodeError:
                    findings["api_root_accessible"] = "Partial (Invalid JSON)"
                    print(f"        [-] REST API root returned 200 but with invalid JSON. Snippet: {response_root.text[:200]}")
            elif response_root.status_code in [401, 403]:
                findings["api_root_accessible"] = "Protected"
                findings["details"] = f"REST API root ({wp_json_url}) is protected (Status: {response_root.status_code}). This is a good security measure if public API access is not needed."
                print(f"        [+] REST API root is protected (Status: {response_root.status_code}).")
                state.add_remediation_suggestion("rest_api_protected", {
                    "source": "WP Analyzer (REST API)", "description": "The WordPress REST API root is protected (e.g., via authentication or IP whitelist).",
                    "severity": "Info", "remediation": "This is a good security practice if full public REST API access is not required. Ensure protection methods are robust."})
            elif response_root.status_code == 404:
                findings["api_root_accessible"] = False
                findings["details"] = f"REST API root ({wp_json_url}) not found (404). REST API might be disabled."
                print(f"        [-] REST API root not found (404). Might be disabled via plugin or server rule.")
            else:
                findings["api_root_accessible"] = "Error"
                findings["details"] = f"REST API root ({wp_json_url}) returned unexpected status: {response_root.status_code}."
                print(f"        [?] REST API root returned unexpected status: {response_root.status_code}.")
        else:
            findings["api_root_accessible"] = "Error (No Response)"
            findings["details"] = f"Request to REST API root ({wp_json_url}) failed."
            print(f"        [-] Request to REST API root failed.")
    except Exception as e_root:
        findings["api_root_accessible"] = f"Error ({type(e_root).__name__})"
        findings["details"] = f"Exception during REST API root check: {e_root}"
        print(f"      [-] Exception during REST API root check: {e_root}")

    # 2. Unauthenticated Core Endpoint Checks (only if API root seems somewhat accessible)
    if findings["api_root_accessible"] is True or findings["api_root_accessible"] == "Partial (Invalid JSON)":
        core_endpoints_to_check = {
            "users": "/wp-json/wp/v2/users?context=view&per_page=5", # context=view for unauth, per_page to get a few
            "posts": "/wp-json/wp/v2/posts?context=view&per_page=3",
            "pages": "/wp-json/wp/v2/pages?context=view&per_page=3",
            "media": "/wp-json/wp/v2/media?context=view&per_page=3",
            "settings": "/wp-json/wp/v2/settings", # Usually requires auth
            "categories": "/wp-json/wp/v2/categories?context=view&per_page=5&orderby=count&order=desc", # NEW
            "tags": "/wp-json/wp/v2/tags?context=view&per_page=5&orderby=count&order=desc" # NEW
        }
        singular_map = {"posts": "post", "pages": "page", "categories": "category", "tags": "tag", "media": "media", "users": "user"}

        print("      Checking unauthenticated access to common core REST API endpoints...")
        for key, path in core_endpoints_to_check.items():
            endpoint_url = urljoin(target_url.rstrip('/'), path)
            findings["core_endpoint_access"][key]["status"] = "Checking"
            try:
                resp_ep = make_request(endpoint_url, config, method="GET", timeout=7)
                if resp_ep:
                    findings["core_endpoint_access"][key]["status_code"] = resp_ep.status_code
                    if resp_ep.status_code == 200:
                        try:
                            data_ep = resp_ep.json()
                            findings["core_endpoint_access"][key]["accessible_unauth"] = True
                            
                            if key == "users":
                                if isinstance(data_ep, list):
                                    findings["core_endpoint_access"][key]["count_unauth"] = len(data_ep)
                                    if data_ep: findings["core_endpoint_access"][key]["data_preview"] = str(data_ep[0])[:150] + "..."
                                    for user_item in data_ep: # Iterate through returned users (up to per_page limit)
                                        user_detail = {
                                            "id": user_item.get("id"), "name": user_item.get("name"),
                                            "slug": user_item.get("slug"), "link": user_item.get("link"),
                                            "description": (user_item.get("description")[:75] + "..." if user_item.get("description") else None)
                                        }
                                        findings["core_endpoint_access"][key]["exposed_user_details"].append({k:v for k,v in user_detail.items() if v is not None})
                                    if findings["core_endpoint_access"][key]["exposed_user_details"]:
                                        print(f"        [!] User data exposed via {path}: {len(findings['core_endpoint_access'][key]['exposed_user_details'])} users listed with details.")
                                else: # Should be a list for users endpoint
                                     print(f"        [?] User endpoint {path} returned 200 but data format was unexpected: {type(data_ep)}")
                            
                            elif key in ["posts", "pages", "media"]:
                                if isinstance(data_ep, list):
                                    findings["core_endpoint_access"][key]["count_unauth"] = len(data_ep)
                                    if data_ep: findings["core_endpoint_access"][key]["data_preview"] = str(data_ep[0])[:150] + "..."
                                    print(f"        [i] Core endpoint {path} accessible unauthenticated, returned {len(data_ep)} item(s).")
                                    author_ids_found = set()
                                    for item in data_ep:
                                        if "author" in item and isinstance(item["author"], int):
                                            author_ids_found.add(item["author"])
                                    if author_ids_found:
                                        findings["core_endpoint_access"][key]["exposes_author_info"] = True
                                        findings["core_endpoint_access"][key]["author_info_preview"] = sorted(list(author_ids_found))
                                        print(f"          [!] Endpoint {path} exposes author IDs: {findings['core_endpoint_access'][key]['author_info_preview']}")
                                        key_singular = singular_map.get(key, key)
                                        state.add_remediation_suggestion(f"rest_api_core_{key}_exposes_author_ids", {
                                            "source": "WP Analyzer (REST API)",
                                            "description": f"Core REST API endpoint '{path}' for '{key}' exposes author IDs. This could potentially be correlated with user information if the user endpoint is also exposed or through other enumeration techniques.",
                                            "severity": "Low",
                                            "remediation": f"Consider if exposing author IDs is necessary for unauthenticated users. You can use filters like 'rest_prepare_{key_singular}' to modify the API response and remove or obfuscate author information for unauthenticated requests."
                                        })
                                else: # Should be a list for these endpoints
                                     print(f"        [?] Endpoint {path} returned 200 but data format was unexpected: {type(data_ep)}")

                            elif key in ["categories", "tags"]:
                                if isinstance(data_ep, list):
                                    findings["core_endpoint_access"][key]["count_unauth"] = len(data_ep)
                                    if data_ep: findings["core_endpoint_access"][key]["data_preview"] = str(data_ep[0])[:150] + "..."
                                    print(f"        [i] Core endpoint {path} accessible unauthenticated, returned {len(data_ep)} item(s).")
                                else: # Should be a list
                                     print(f"        [?] Endpoint {path} returned 200 but data format was unexpected: {type(data_ep)}")
                            
                            elif key == "settings": # Settings endpoint returns a dict
                                if isinstance(data_ep, dict):
                                    findings["core_endpoint_access"][key]["data_preview"] = str(data_ep)[:150] + "..."
                                    print(f"        [!] Core endpoint {path} accessible unauthenticated, returned data.")
                                else:
                                     print(f"        [?] Settings endpoint {path} returned 200 but data format was unexpected: {type(data_ep)}")

                            # Generic remediation for exposed core endpoints (if not handled by more specific ones above)
                            # The original remediation logic:
                            if key in ["users", "settings"] or \
                               (key in ["posts", "pages", "media", "categories", "tags"] and findings["core_endpoint_access"][key].get("count_unauth", 0) > 0):
                                severity = "Medium" if key in ["users", "settings"] else "Low"
                                if key in ["categories", "tags"] and findings["core_endpoint_access"][key].get("count_unauth", 0) > 0 : severity = "Info" # Downgrade for taxonomies

                                # Avoid duplicate remediation if a more specific one (like author ID exposure) was added
                                # This general one is still good for the base exposure.
                                state.add_remediation_suggestion(f"rest_api_core_{key}_exposed", {
                                    "source": "WP Analyzer (REST API)",
                                    "description": f"Core REST API endpoint '{path}' is accessible to unauthenticated users and returns data. This may expose sensitive information or site structure details ({key}).",
                                    "severity": severity,
                                    "remediation": f"Restrict public access to the '{path}' REST API endpoint if not necessary. Use security plugins or custom filters (e.g., 'rest_authentication_errors', 'rest_{singular_map.get(key, key)}_query') to enforce authentication and limit data exposure."
                                })
                            
                            # CORS Check for an accessible core endpoint (e.g., posts)
                            if key == "posts" and findings["core_endpoint_access"][key]["accessible_unauth"] is True:
                                ep_cors_policy = resp_ep.headers.get("Access-Control-Allow-Origin")
                                if ep_cors_policy:
                                    print(f"        [i] CORS policy for {path}: Access-Control-Allow-Origin: {ep_cors_policy}")
                                    if ep_cors_policy == "*":
                                        state.add_remediation_suggestion(f"rest_api_core_{key}_permissive_cors", {
                                            "source": "WP Analyzer (REST API)",
                                            "description": f"The REST API endpoint '{path}' has a permissive CORS policy (Access-Control-Allow-Origin: *).",
                                            "severity": "Low",
                                            "remediation": f"Restrict the Access-Control-Allow-Origin header for '{path}' to only trusted domains or ensure no sensitive, cookie-authenticated GET operations are exposed."
                                        })

                        except json.JSONDecodeError:
                             findings["core_endpoint_access"][key]["accessible_unauth"] = "Partial (Invalid JSON)"
                             print(f"        [?] Core endpoint {path} returned 200 but with invalid JSON.")
                    elif resp_ep.status_code in [401, 403]:
                        findings["core_endpoint_access"][key]["accessible_unauth"] = False
                        print(f"        [+] Core endpoint {path} correctly protected (Status: {resp_ep.status_code}).")
                    else:
                        findings["core_endpoint_access"][key]["accessible_unauth"] = "Unexpected Status"
                        print(f"        [?] Core endpoint {path} returned status {resp_ep.status_code}.")
                else:
                    findings["core_endpoint_access"][key]["status"] = "Error (No Response)"
            except Exception as e_ep:
                findings["core_endpoint_access"][key]["status"] = f"Error ({type(e_ep).__name__})"
            if findings["core_endpoint_access"][key]["status"] == "Checking": findings["core_endpoint_access"][key]["status"] = "Completed"
    else:
        print("      Skipping core endpoint checks as REST API root is not accessible or protected.")
        for key in findings["core_endpoint_access"]: findings["core_endpoint_access"][key]["status"] = "Skipped (API Root Inaccessible)"

    # 3. Analyze Custom/Plugin Endpoints for Sensitive Parameter Exposure (Unauthenticated GET)
    if findings["api_root_accessible"] is True and findings["namespaces"]:
        print("      Analyzing custom/plugin REST API endpoints for potential unauthenticated data exposure via GET parameters...")
        for ns_data in findings["namespaces"]:
            if not ns_data.get("is_core_common", True): # Only check custom namespaces
                for route_info in ns_data.get("routes", []):
                    if "GET" in route_info.get("methods", []):
                        route_args = route_info.get("args_summary", {})
                        for arg_name, arg_details in route_args.items():
                            # Check if arg_name contains any sensitive keyword and is not explicitly required
                            # We assume if 'required' is not present or False, it's optional.
                            is_potentially_sensitive_param = any(keyword in arg_name.lower() for keyword in SENSITIVE_PARAM_KEYWORDS)
                            is_optional_param = not arg_details.get("required", False) 

                            if is_potentially_sensitive_param and is_optional_param:
                                test_param_value = "1" # A common test value for IDs, etc.
                                if any(kw in arg_name.lower() for kw in ['search', 's', 'query', 'filter']):
                                    test_param_value = "test"
                                
                                test_url = f"{route_info['full_route_url']}?{arg_name}={test_param_value}"
                                print(f"        Testing custom route: {route_info['path']} with param: {arg_name}={test_param_value}")
                                try:
                                    resp_custom_ep = make_request(test_url, config, method="GET", timeout=5)
                                    if resp_custom_ep and resp_custom_ep.status_code == 200:
                                        try:
                                            data_custom_ep = resp_custom_ep.json()
                                            if data_custom_ep: # If it returns non-empty JSON data
                                                preview = str(data_custom_ep)[:200] + "..." if data_custom_ep else "Empty response"
                                                print(f"          [!] Potential exposure on {ns_data['name']}{route_info['path']} via '{arg_name}'. Status: 200. Preview: {preview}")
                                                findings["custom_endpoint_analysis"].append({
                                                    "namespace": ns_data['name'],
                                                    "route": route_info['path'],
                                                    "parameter": arg_name,
                                                    "test_url": test_url,
                                                    "status_code": resp_custom_ep.status_code,
                                                    "response_preview": preview
                                                })
                                                state.add_remediation_suggestion(f"rest_api_custom_ep_sensitive_param_{ns_data['name']}_{arg_name}", {
                                                    "source": "WP Analyzer (REST API)",
                                                    "description": f"Custom REST API endpoint '{ns_data['name']}{route_info['path']}' allows unauthenticated GET requests with parameter '{arg_name}' and returns data. This parameter seems potentially sensitive.",
                                                    "severity": "Medium", # Could be High depending on data
                                                    "remediation": f"Review the endpoint '{ns_data['name']}{route_info['path']}'. Ensure that unauthenticated access with parameter '{arg_name}' does not expose sensitive information. Implement proper authentication and authorization checks. Sanitize all input parameters."
                                                })
                                        except json.JSONDecodeError:
                                            print(f"          [?] Custom route {route_info['path']} with param '{arg_name}' returned 200 but with invalid JSON.")
                                    # elif resp_custom_ep:
                                        # print(f"          Custom route {route_info['path']} with param '{arg_name}' returned {resp_custom_ep.status_code}")
                                except Exception as e_custom_ep:
                                    print(f"          Error testing custom route {route_info['path']} with param '{arg_name}': {e_custom_ep}")
    
    # Call placeholder for authenticated checks
    analyze_rest_api_authenticated(state, config, target_url, findings_key=findings_key)


    # Finalize overall status and details
    final_details_parts = []
    if findings["api_root_accessible"] is True: final_details_parts.append(f"API root at {wp_json_url} is accessible.")
    elif findings["api_root_accessible"] == "Protected": final_details_parts.append(f"API root at {wp_json_url} is protected.")
    elif findings["api_root_accessible"] is False: final_details_parts.append(f"API root at {wp_json_url} seems disabled/not found.")
    
    if findings["namespaces"]:
        num_ns = len(findings['namespaces'])
        custom_ns_count = len(findings['custom_namespaces_identified'])
        final_details_parts.append(f"Discovered {num_ns} namespaces ({custom_ns_count} custom/plugin, {num_ns - custom_ns_count} core/common).")
    
    exposed_core_eps = [k for k,v in findings["core_endpoint_access"].items() if v.get("accessible_unauth") is True and (v.get("count_unauth",0) > 0 or v.get("data_preview") or v.get("exposed_user_details"))]
    if exposed_core_eps: final_details_parts.append(f"Unauthenticated access to core endpoints: {', '.join(exposed_core_eps)}.")

    if findings["core_endpoint_access"]["users"].get("exposed_user_details"):
        final_details_parts.append(f"User details exposed via REST API for {len(findings['core_endpoint_access']['users']['exposed_user_details'])} users.")

    exposed_author_eps = [k for k,v in findings["core_endpoint_access"].items() if k in ["posts", "pages", "media"] and v.get("exposes_author_info")]
    if exposed_author_eps:
        final_details_parts.append(f"Author IDs exposed via: {', '.join(exposed_author_eps)}.")
    
    if findings["custom_endpoint_analysis"]:
        final_details_parts.append(f"Found {len(findings['custom_endpoint_analysis'])} custom endpoints with potentially sensitive unauthenticated GET parameter access.")

    if findings["api_root_cors_policy"] == "*":
        final_details_parts.append("Permissive CORS policy ('*') on API root.")
    elif findings["api_root_cors_policy"]:
         final_details_parts.append(f"API root CORS policy: {findings['api_root_cors_policy']}.")


    findings["details"] = " ".join(final_details_parts) if final_details_parts else "General REST API analysis performed. See specific findings."
    findings["status"] = "Completed"
    state.update_specific_finding(module_key, findings_key, findings)
    print(f"    [+] General REST API analysis finished. Details: {findings['details']}")
