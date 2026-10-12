import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
import time
from core.utils import sanitize_filename, user_confirm # Core utils needed here
from .utils import make_request # Local utils for requests

# Known XML-RPC methods and their potential implications
KNOWN_METHODS_IMPLICATIONS = {
    "system.listMethods": {"category": "System Information", "risk": "Low", "info": "Lists available XML-RPC methods."},
    "system.multicall": {"category": "System Utility", "risk": "Medium", "info": "Allows multiple XML-RPC calls in a single request. Can be abused for brute-force amplification."},
    "system.getCapabilities": {"category": "System Information", "risk": "Low", "info": "Describes the capabilities of the XML-RPC server."},
    "pingback.ping": {"category": "Pingback", "risk": "Medium", "info": "Used for pingbacks. Can be abused for DDoS amplification and SSRF."},
    "pingback.get znači": {"category": "Pingback", "risk": "Low", "info": "Retrieves existing pingbacks."},
    "wp.getUsersBlogs": {"category": "User Management", "risk": "Medium", "info": "Can be used to enumerate usernames if not properly restricted."},
    "wp.getUser": {"category": "User Management", "risk": "Medium", "info": "Retrieves user information. Requires authentication."},
    "wp.getProfile": {"category": "User Management", "risk": "Medium", "info": "Retrieves user profile. Requires authentication."},
    "wp.getAuthors": {"category": "User Management", "risk": "Medium", "info": "Can enumerate authors/usernames."},
    "wp.getPage": {"category": "Content Access", "risk": "Low", "info": "Retrieves a page. Requires authentication for private content."},
    "wp.getPages": {"category": "Content Access", "risk": "Low", "info": "Retrieves multiple pages."},
    "wp.newPost": {"category": "Content Manipulation", "risk": "High", "info": "Allows creating new posts. Requires authentication."},
    "wp.editPost": {"category": "Content Manipulation", "risk": "High", "info": "Allows editing posts. Requires authentication."},
    "wp.deletePost": {"category": "Content Manipulation", "risk": "High", "info": "Allows deleting posts. Requires authentication."},
    "metaWeblog.newPost": {"category": "Content Manipulation", "risk": "High", "info": "MetaWeblog API equivalent for creating posts."},
    "metaWeblog.editPost": {"category": "Content Manipulation", "risk": "High", "info": "MetaWeblog API equivalent for editing posts."},
    "metaWeblog.getUsersBlogs": {"category": "User Management", "risk": "Medium", "info": "Similar to wp.getUsersBlogs, can enumerate usernames."},
    "blogger.getUsersBlogs": {"category": "User Management", "risk": "Medium", "info": "Blogger API, can also be used for username enumeration."},
    "demo.sayHello": {"category": "Demo/Test", "risk": "Low", "info": "A simple test method, indicates XML-RPC is responsive."},
    "demo.addTwoNumbers": {"category": "Demo/Test", "risk": "Low", "info": "Another simple test method."},
    # Add more as they become relevant
}

def _check_specific_method(xmlrpc_url, config, method_name, params_xml=""):
    """Helper function to test a specific XML-RPC method."""
    payload = f"<methodCall><methodName>{method_name}</methodName><params>{params_xml}</params></methodCall>"
    response = make_request(xmlrpc_url, config, method="POST", data=payload, timeout=config.get("analyzer_timeout", 10))
    return response

def analyze_xml_rpc(state, config, target_url):
    """Analyzes the XML-RPC interface, including methods, potential SSRF, brute-force, and user enumeration."""
    module_key = "wp_analyzer"
    analyzer_findings = state.get_module_findings(module_key, {})
    if "xml_rpc" not in analyzer_findings:
        analyzer_findings["xml_rpc"] = {"status": "Not Started", "details": {}, "vulnerabilities": []}
    xmlrpc_details = analyzer_findings["xml_rpc"]["details"] # Direct access to details
    xmlrpc_vulnerabilities = analyzer_findings["xml_rpc"]["vulnerabilities"]

    xmlrpc_url = urljoin(target_url.rstrip('/'), "/xmlrpc.php")
    xmlrpc_details["url_checked"] = xmlrpc_url
    print(f"    Checking XML-RPC: {xmlrpc_url}")

    # Initial check using HEAD
    head_response = make_request(xmlrpc_url, config, method="HEAD", timeout=config.get("analyzer_timeout_short", 5))
    if not head_response or head_response.status_code != 200:
        status_code = head_response.status_code if head_response else 'Request Failed'
        analyzer_findings["xml_rpc"]["status"] = f"Disabled/Blocked (Status: {status_code})"
        print(f"    [-] XML-RPC seems disabled or blocked at {xmlrpc_url} (Status: {status_code}).")
        state.update_module_findings(module_key, analyzer_findings)
        return

    analyzer_findings["xml_rpc"]["status"] = "Enabled (Responded 200 to HEAD)"
    print(f"    [i] XML-RPC interface found at {xmlrpc_url}. Probing methods...")

    # --- Method Listing and Analysis ---
    listed_methods = []
    list_methods_payload = "<methodCall><methodName>system.listMethods</methodName><params></params></methodCall>"
    response = make_request(xmlrpc_url, config, method="POST", data=list_methods_payload, timeout=config.get("analyzer_timeout", 10))

    pingback_ping_found = False
    system_multicall_found = False
    user_enum_methods_found = []

    if response and response.status_code == 200 and "system.listMethods" in response.text:
        xmlrpc_details["system.listMethods_status"] = "Accessible"
        print(f"    [+] XML-RPC system.listMethods successful.")
        try:
            root = ET.fromstring(response.content)
            methods_xml = root.findall('.//methodResponse/params/param/value/array/data/value/string')
            listed_methods = [m.text for m in methods_xml if m.text]
            if listed_methods:
                xmlrpc_details["available_methods_count"] = len(listed_methods)
                xmlrpc_details["available_methods"] = listed_methods
                print(f"      [i] Found {len(listed_methods)} XML-RPC methods.")
                
                detailed_method_info = {}
                for method in listed_methods:
                    implication = KNOWN_METHODS_IMPLICATIONS.get(method, {"category": "Unknown", "risk": "N/A", "info": "No specific information."})
                    detailed_method_info[method] = implication
                    if method == "pingback.ping":
                        pingback_ping_found = True
                        xmlrpc_vulnerabilities.append({
                            "type": "XML-RPC Pingback Enabled",
                            "description": "The 'pingback.ping' method is enabled. This can be abused for DDoS amplification or internal port scanning (SSRF).",
                            "severity": "Medium",
                            "remediation": "Disable XML-RPC if not needed, or selectively disable pingbacks using filters or security plugins like 'Disable XML-RPC Pingback'."
                        })
                    elif method == "system.multicall":
                        system_multicall_found = True
                        xmlrpc_vulnerabilities.append({
                            "type": "XML-RPC system.multicall Enabled",
                            "description": "The 'system.multicall' method is enabled. This can be used to amplify brute-force attacks by sending multiple login attempts in one HTTP request.",
                            "severity": "Medium",
                            "remediation": "Disable XML-RPC if not needed, or use a security plugin to block or rate-limit system.multicall."
                        })
                    elif method in ["wp.getUsersBlogs", "metaWeblog.getUsersBlogs", "blogger.getUsersBlogs", "wp.getAuthors"]:
                        if method not in user_enum_methods_found:
                             user_enum_methods_found.append(method)
                xmlrpc_details["methods_analysis"] = detailed_method_info
                if user_enum_methods_found:
                    xmlrpc_vulnerabilities.append({
                        "type": "XML-RPC User Enumeration Methods Enabled",
                        "description": f"Methods like {', '.join(user_enum_methods_found)} are enabled, which could potentially be used for username enumeration.",
                        "severity": "Medium",
                        "remediation": "Disable these XML-RPC methods if not essential, or use security plugins to restrict access or harden against enumeration."
                    })

            else:
                print("      [i] system.listMethods response parsed, but no methods listed.")
                xmlrpc_details["available_methods_count"] = 0
        except ET.ParseError:
            xmlrpc_details["system.listMethods_status"] = "Parsing Error"
            print("      [-] Could not parse XML-RPC system.listMethods response.")
    elif response:
        xmlrpc_details["system.listMethods_status"] = f"Failed (Status: {response.status_code})"
        print(f"    [-] system.listMethods failed (Status: {response.status_code}). Attempting to check for common individual methods.")
        # If listMethods fails, try to detect some common methods individually
        common_methods_to_check = ["pingback.ping", "system.multicall", "wp.getUsersBlogs", "demo.sayHello"]
        found_individual_methods = []
        for method_to_check in common_methods_to_check:
            # A simple check, not trying to invoke with full params here, just see if it's recognized
            # For demo.sayHello, it doesn't need params.
            check_resp = _check_specific_method(xmlrpc_url, config, method_to_check)
            if check_resp and check_resp.status_code == 200 and method_to_check in check_resp.text: # Basic check
                 found_individual_methods.append(method_to_check)
                 if method_to_check == "pingback.ping": pingback_ping_found = True
                 if method_to_check == "system.multicall": system_multicall_found = True
                 if method_to_check == "wp.getUsersBlogs" and method_to_check not in user_enum_methods_found: user_enum_methods_found.append(method_to_check)
                 print(f"      [+] Individually detected method: {method_to_check}")
            elif check_resp and "faultCode" in check_resp.text: # Method exists but requires params or auth
                 found_individual_methods.append(method_to_check) # Still counts as found
                 if method_to_check == "pingback.ping": pingback_ping_found = True # Assume it's there
                 if method_to_check == "system.multicall": system_multicall_found = True
                 if method_to_check == "wp.getUsersBlogs" and method_to_check not in user_enum_methods_found: user_enum_methods_found.append(method_to_check)
                 print(f"      [i] Individually detected method (faulted, likely exists): {method_to_check}")


        if found_individual_methods:
            xmlrpc_details["individually_detected_methods"] = found_individual_methods
            # Update vulnerabilities based on individual detection
            if pingback_ping_found and not any(v["type"] == "XML-RPC Pingback Enabled" for v in xmlrpc_vulnerabilities):
                 xmlrpc_vulnerabilities.append({"type": "XML-RPC Pingback Enabled", "description": "...", "severity": "Medium", "remediation": "..."}) # Abridged
            if system_multicall_found and not any(v["type"] == "XML-RPC system.multicall Enabled" for v in xmlrpc_vulnerabilities):
                 xmlrpc_vulnerabilities.append({"type": "XML-RPC system.multicall Enabled", "description": "...", "severity": "Medium", "remediation": "..."}) # Abridged
            if user_enum_methods_found and not any(v["type"] == "XML-RPC User Enumeration Methods Enabled" for v in xmlrpc_vulnerabilities):
                 xmlrpc_vulnerabilities.append({"type": "XML-RPC User Enumeration Methods Enabled", "description": "...", "severity": "Medium", "remediation": "..."}) # Abridged


    else:
        xmlrpc_details["system.listMethods_status"] = "Request Failed"
        print(f"    [-] system.listMethods request failed.")

    # --- Check system.getCapabilities ---
    if config.get("analyzer_xmlrpc_check_capabilities", True):
        print("    [i] Checking system.getCapabilities...")
        cap_resp = _check_specific_method(xmlrpc_url, config, "system.getCapabilities")
        if cap_resp and cap_resp.status_code == 200 and "system.getCapabilities" in cap_resp.text:
            try:
                root = ET.fromstring(cap_resp.content)
                capabilities = {}
                for member in root.findall('.//methodResponse/params/param/value/struct/member'):
                    name = member.find('name').text
                    value_node = member.find('value')
                    # This can be complex, just grabbing basic types for now
                    val_text = value_node.find('./*[1]').text if value_node.find('./*[1]') is not None else 'N/A'
                    capabilities[name] = val_text
                if capabilities:
                    xmlrpc_details["system_capabilities"] = capabilities
                    print(f"      [+] system.getCapabilities successful. Found: {', '.join(capabilities.keys())}")
                else:
                    xmlrpc_details["system_capabilities"] = "Parsed, but no capabilities listed."
                    print("      [i] system.getCapabilities response parsed, but no capabilities listed.")
            except ET.ParseError:
                xmlrpc_details["system_capabilities"] = "Parsing Error"
                print("      [-] Could not parse system.getCapabilities response.")
        elif cap_resp:
            xmlrpc_details["system_capabilities"] = f"Failed (Status: {cap_resp.status_code})"
            print(f"    [-] system.getCapabilities failed (Status: {cap_resp.status_code}).")
        else:
            xmlrpc_details["system_capabilities"] = "Request Failed"
            print(f"    [-] system.getCapabilities request failed.")


    # --- XML-RPC Pingback SSRF Test ---
    xmlrpc_details.setdefault("ssrf_via_pingback_test", {"status": "Not Run"})
    ssrf_test_details = xmlrpc_details["ssrf_via_pingback_test"]
    run_ssrf_test = config.get("analyzer_xmlrpc_ssrf_test_enabled", False) and pingback_ping_found

    if run_ssrf_test:
        if user_confirm("Perform XML-RPC Pingback SSRF test? (Sends outbound requests from target)", config):
            print("    [i] Performing XML-RPC Pingback SSRF test...")
            ssrf_test_details["status"] = "Running"
            ssrf_test_details["targets_tested"] = []
            ssrf_test_details["responses"] = {}

            oast_domain = config.get("oast_domain_placeholder", "YOUR_OAST_DOMAIN_HERE")
            pingback_targets = list(config.get("analyzer_xmlrpc_ssrf_pingback_targets", []))

            if "YOUR_OAST_DOMAIN_HERE" not in oast_domain and oast_domain:
                unique_id = f"{sanitize_filename(urlparse(target_url).netloc)}_{int(time.time())}"
                oast_target = f"http://{unique_id}.{oast_domain}"
                pingback_targets.insert(0, oast_target)

            if not pingback_targets:
                ssrf_test_details["status"] = "Skipped (No Targets)"
                print("      [!] No valid targets configured for XML-RPC SSRF pingback test.")
            else:
                for pb_target in pingback_targets:
                    ssrf_test_details["targets_tested"].append(pb_target)
                    print(f"      Pinging: {pb_target} via XML-RPC pingback...")
                    source_ping_url = urljoin(target_url, f'/pingback-ssrf-test-source-{int(time.time())}')
                    ssrf_payload = f"<methodCall><methodName>pingback.ping</methodName><params><param><value><string>{pb_target}</string></value></param><param><value><string>{source_ping_url}</string></value></param></params></methodCall>"
                    ssrf_response = make_request(xmlrpc_url, config, method="POST", data=ssrf_payload, timeout=config.get("analyzer_timeout_long", 20))

                    response_summary = "No response"
                    response_status = "Request Failed"
                    response_snippet = ""

                    if ssrf_response:
                        response_summary = f"Status: {ssrf_response.status_code}, Len: {len(ssrf_response.text)}"
                        response_snippet = ssrf_response.text[:200]
                        text_lower = ssrf_response.text.lower()
                        if "faultcode" not in text_lower and ssrf_response.status_code == 200 : # Success is usually 200 and no fault
                            response_status = "Potential SSRF (No Fault)"
                            print(f"        [!!!] XML-RPC pingback to {pb_target} did NOT return faultCode. Check OAST/target logs. {response_summary}")
                            xmlrpc_vulnerabilities.append({
                                "type": "Potential SSRF via XML-RPC Pingback",
                                "description": f"Pingback to '{pb_target}' succeeded (HTTP {ssrf_response.status_code}, no faultCode in response). This indicates potential SSRF. Verify by checking logs on the target or OAST service.",
                                "severity": "High",
                                "remediation": "Disable XML-RPC pingbacks. If using an OAST service, confirm interaction. Investigate internal network exposure if applicable.",
                                "target_tested": pb_target,
                                "response_snippet": response_snippet
                            })
                        else:
                            response_status = "Fault Code Returned or Error Status"
                            print(f"        [i] XML-RPC pingback to {pb_target} returned faultCode or error status (likely blocked/failed). {response_summary}")
                    else:
                         print(f"        [-] XML-RPC pingback request to {pb_target} failed.")

                    ssrf_test_details["responses"][pb_target] = {
                        "status": response_status,
                        "details": response_summary,
                        "snippet": response_snippet
                    }
                ssrf_test_details["status"] = "Completed"
        else:
            ssrf_test_details["status"] = "Skipped (User Declined)"
    else:
        if not pingback_ping_found and analyzer_findings["xml_rpc"]["status"].startswith("Enabled"):
             ssrf_test_details["status"] = "Skipped (Pingback Method Not Found/Accessible)"
        elif not config.get("analyzer_xmlrpc_ssrf_test_enabled", False):
             ssrf_test_details["status"] = "Skipped (Disabled in Config)"
        elif "status" not in ssrf_test_details or ssrf_test_details["status"] == "Not Run": # Ensure a status is set if not run for other reasons
             ssrf_test_details["status"] = "Skipped (Condition Not Met)"
    
    # --- Brute-Force Amplification Check (system.multicall) ---
    xmlrpc_details.setdefault("brute_force_amplification_check", {"status": "Not Run"})
    bf_amp_check = xmlrpc_details["brute_force_amplification_check"]
    if system_multicall_found and config.get("analyzer_xmlrpc_check_multicall_bruteforce", True):
        bf_amp_check["status"] = "system.multicall is enabled"
        bf_amp_check["info"] = "The 'system.multicall' method can be abused to amplify brute-force attacks by sending many login attempts in a single HTTP request. This makes it harder for rate-limiting tools to detect and block attacks."
        print(f"    [!] system.multicall is enabled. Potential for brute-force amplification.")
        # Note: Actively testing this would involve sending actual login attempts, which is out of scope for a simple check.
        # We've already added a vulnerability entry if system.multicall is found.
    elif not system_multicall_found:
         bf_amp_check["status"] = "system.multicall not found or inaccessible."

    # --- User Enumeration Check ---
    xmlrpc_details.setdefault("user_enumeration_check", {"status": "Not Run"})
    user_enum_check = xmlrpc_details["user_enumeration_check"]
    if user_enum_methods_found and config.get("analyzer_xmlrpc_user_enum_enabled", False):
        if user_confirm(f"Attempt XML-RPC user enumeration via {', '.join(user_enum_methods_found)}? (Sends multiple requests)", config):
            user_enum_check["status"] = "Running"
            user_enum_check["methods_used"] = user_enum_methods_found
            user_enum_check["found_users"] = []
            print(f"    [i] Attempting user enumeration via {', '.join(user_enum_methods_found)}...")
            
            # Try with wp.getUsersBlogs or metaWeblog.getUsersBlogs first as they are common
            enum_method_to_try = None
            if "wp.getUsersBlogs" in user_enum_methods_found:
                enum_method_to_try = "wp.getUsersBlogs"
            elif "metaWeblog.getUsersBlogs" in user_enum_methods_found:
                enum_method_to_try = "metaWeblog.getUsersBlogs"
            elif "blogger.getUsersBlogs" in user_enum_methods_found:
                enum_method_to_try = "blogger.getUsersBlogs"
            # wp.getAuthors might require different handling or might not be as effective with dummy credentials

            if enum_method_to_try:
                # Try with dummy credentials, sometimes it leaks usernames even with invalid auth
                # This is a simplified attempt; real enumeration can be more complex
                dummy_user, dummy_pass = "invaliduser", "invalidpass"
                params_xml = f"<param><value><string>{dummy_user}</string></value></param><param><value><string>{dummy_pass}</string></value></param>"
                if enum_method_to_try == "wp.getAuthors": # wp.getAuthors might take blog_id, user, pass
                    # For simplicity, we'll try it like getUsersBlogs; a more targeted approach might be needed
                     params_xml = f"<param><value><int>1</int></value></param>{params_xml}"


                enum_resp = _check_specific_method(xmlrpc_url, config, enum_method_to_try, params_xml)
                
                if enum_resp and enum_resp.status_code == 200:
                    # Successful response, check for user info (this is highly dependent on server response format)
                    # A common pattern for fault is <fault><value><struct>...
                    if "faultCode" not in enum_resp.text.lower() and "username" in enum_resp.text.lower(): # Very basic check
                        # This part needs more sophisticated parsing based on actual successful responses
                        # For now, we'll just indicate a potential leak if no fault and "username" is in text
                        print(f"      [!] Potential user information leak via {enum_method_to_try} with dummy credentials. Manual verification needed.")
                        user_enum_check["potential_leak_with_dummy_creds"] = True
                        xmlrpc_vulnerabilities.append({
                            "type": "Potential User Info Leak via XML-RPC",
                            "description": f"The method '{enum_method_to_try}' responded successfully to dummy credentials and contained 'username' in the response. This might indicate a user information leak. Manual verification is required.",
                            "severity": "Medium",
                            "remediation": "Ensure XML-RPC methods like wp.getUsersBlogs are properly restricted or disabled if not needed. Use strong passwords and limit authentication attempts."
                        })
                    elif "faultCode" in enum_resp.text.lower():
                        # Check for specific fault codes that might indicate username validity (e.g., incorrect password for user X)
                        # Example: "Incorrect username or password." (faultCode 403)
                        try:
                            fault_root = ET.fromstring(enum_resp.content)
                            fault_string_node = fault_root.find('.//fault/value/struct/member[name="faultString"]/value/string')
                            fault_code_node = fault_root.find('.//fault/value/struct/member[name="faultCode"]/value/int')
                            if fault_string_node is not None and fault_code_node is not None:
                                fault_string = fault_string_node.text
                                fault_code = fault_code_node.text
                                user_enum_check["fault_response"] = {"code": fault_code, "string": fault_string}
                                print(f"      [i] {enum_method_to_try} returned fault {fault_code}: {fault_string}")
                                # Some plugins might reveal if a username is valid with a specific fault for "incorrect password"
                                # This is a placeholder for more advanced logic
                        except ET.ParseError:
                            print(f"      [-] Could not parse fault response from {enum_method_to_try}.")
                elif enum_resp:
                     print(f"      [-] User enumeration attempt with {enum_method_to_try} failed with status {enum_resp.status_code}.")
                else:
                     print(f"      [-] User enumeration attempt with {enum_method_to_try} request failed.")
            
            # Placeholder for trying author ID enumeration if wp.getAuthors is present and above failed
            # if "wp.getAuthors" in user_enum_methods_found and not user_enum_check["found_users"]:
            #   print("    [i] Attempting user enumeration via wp.getAuthors with author IDs...")
            #   for i in range(1, config.get("analyzer_xmlrpc_user_enum_max_ids", 5) + 1):
            #       # Construct payload for wp.getAuthors with author ID i
            #       # Parse response, look for usernames
            #       pass

            user_enum_check["status"] = "Completed" # Or "Partially Completed"
        else:
            user_enum_check["status"] = "Skipped (User Declined)"
    else:
        if not user_enum_methods_found and analyzer_findings["xml_rpc"]["status"].startswith("Enabled"):
            user_enum_check["status"] = "Skipped (No Suitable Methods Found)"
        elif not config.get("analyzer_xmlrpc_user_enum_enabled", False):
            user_enum_check["status"] = "Skipped (Disabled in Config)"

    analyzer_findings["xml_rpc"]["details"] = xmlrpc_details
    analyzer_findings["xml_rpc"]["vulnerabilities"] = xmlrpc_vulnerabilities
    state.update_module_findings(module_key, analyzer_findings)
    print(f"    [+] XML-RPC analysis complete.")
