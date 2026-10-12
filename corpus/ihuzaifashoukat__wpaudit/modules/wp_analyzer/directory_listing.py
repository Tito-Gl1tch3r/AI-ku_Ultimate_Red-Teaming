import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import datetime # For year/month upload paths
from core.utils import sanitize_filename
from .utils import make_request

# --- Enhanced Constants ---
SENSITIVE_FILE_EXTENSIONS = [
    '.log', '.sql', '.bak', '.backup', '.old', '.orig', '.tmp', '.temp', '.swp', '.swo', # Common backups/temp
    '.zip', '.tar', '.gz', '.tgz', '.rar', '.7z', # Archives
    '.sitemap', '.xml', '.json', # Data files that can be sensitive if misconfigured
    '.phps', '.inc', '.asp', '.aspx', '.jsp', '.cgi', # Source code / includes
    '.env', '.env.local', '.env.dev', '.env.prod', '.env.example', # Environment files
    '.config', '.conf', '.cfg', '.ini', '.yml', '.yaml', # Configuration files
    '.sh', '.bash', '.bat', '.ps1', # Scripts
    '.txt', '.md', '.doc', '.docx', '.pdf', '.rtf', # Documents that might be misconfigured
    '.csv', '.xls', '.xlsx', # Data exports
    '.pem', '.key', '.crt', '.p12', '.pfx', '.jks', # Certificates and keys
    '.db', '.sqlite', '.mdb', '.sqlite3', # Database files
    '.DS_Store', '.htpasswd', '.htaccess', '.htusers', # System/Webserver specific
    '.gitconfig', '.gitignore_global', # Git related
    '.npmrc', '.yarnrc', # Package manager configs
    '.bash_history', '.zsh_history', # Shell history
    '.psql_history', '.mysql_history' # DB client history
]
SENSITIVE_FILENAME_KEYWORDS = [
    'debug', 'error', 'trace', 'stacktrace', 'exception',
    'backup', 'bckp', 'bkp', 'dump', 'export', 'archive', 'copy', 'migration',
    'secret', 'password', 'passwd', 'pwd', 'credential', 'token', 'apikey', 'api_key', 'auth', 'access',
    'key', 'privatekey', 'publickey', 'cert', 'certificate',
    'config', 'settings', 'configuration', 'connection', 'conn', 'creds', 'credentials',
    'admin', 'root', 'master', 'sudo',
    'wp-config', 'database', 'shadow', 'htpasswd', '.htusers', 'users', 'accounts',
    'session', 'sensitive', 'internal', 'private', 'confidential', 'secure',
    'composer.lock', 'package-lock.json', 'yarn.lock', # Dependency lock files
    'core', # Core dumps
    'id_rsa', 'id_dsa', 'known_hosts', # SSH related
    'jenkins', 'gitlab', 'github', # CI/CD related
    'payment', 'billing', 'invoice', 'transaction' # Financial data
]

# Constants for content analysis
DEFAULT_MAX_RECURSION_DEPTH = 2
DEFAULT_FETCH_SENSITIVE_FILES = True
DEFAULT_MAX_SENSITIVE_FETCH_PER_DIR = 3
DEFAULT_MAX_FILE_SIZE_TO_FETCH = 1024 * 100  # 100KB limit for fetching file content

SENSITIVE_CONTENT_PATTERNS = {
    "Generic API Key/Token": r'(api_key|apikey|api-key|auth_token|access_token|client_secret|secret_key|token)\s*[:=]\s*[\'"]?([a-zA-Z0-9_\-.~+/=]{20,80})[\'"]?',
    "Generic Password": r'(password|passwd|pwd|pass)\s*[:=]\s*[\'"]?([^\s\'"]{8,64})[\'"]?',
    "AWS Access Key ID": r'AKIA[0-9A-Z]{16}',
    "AWS Secret Key": r'(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])', # More precise
    "Google API Key (AIza)": r'AIza[0-9A-Za-z\\-_]{35}',
    "GitHub Token": r'gh[pousr]_[a-zA-Z0-9]{36}',
    "SSH Private Key Header": r'-----BEGIN ((EC|RSA|DSA|OPENSSH|PGP) )?PRIVATE KEY-----',
    "Database Connection String": r'(mysql|postgres|mongodb(?:srv)?|sqlserver|oracle|mariadb)://[^:]+:[^@]+@[^/\s\'"]+/[^\s\'"]+',
    "Basic Auth Credentials in URL": r'https?://[^:]+:[^@]+@',
    "JWT Token": r'ey[A-Za-z0-9-_=]+\.ey[A-Za-z0-9-_=]+\.(?:[A-Za-z0-9-_.+/=]+)?'
}

# --- Helper Functions ---

def _is_directory_listing(html_content, url_path):
    """Checks if HTML content indicates a directory listing with enhanced heuristics."""
    if not html_content:
        return False
    
    text_content_lower = html_content.lower() # For broad text searches
    soup = BeautifulSoup(html_content, 'lxml')

    # 1. Title checks (common for Apache, Nginx, Lighttpd, IIS)
    title_tag = soup.find('title')
    if title_tag and title_tag.string:
        title_text = title_tag.string.lower()
        # Common patterns: "Index of /path", "Listing of /path", "/path - /"
        if "index of" in title_text and (url_path.lower() in title_text or url_path.lower().strip('/') in title_text):
            return True
        if "listing of" in title_text and (url_path.lower() in title_text or url_path.lower().strip('/') in title_text):
            return True
        if title_text.startswith(url_path.lower().strip('/') + " - /"): # Common with some servers
            return True
        if title_text == url_path.lower().strip('/'): # IIS sometimes just has the path
             # Check for other indicators if title is just path
            if soup.find('pre') and len(soup.find_all('a', href=True)) > 2: return True


    # 2. Presence of "Parent Directory" or "../" link (very common)
    parent_dir_anchor = soup.find('a', href='../')
    if parent_dir_anchor:
        anchor_text_lower = parent_dir_anchor.get_text(strip=True).lower()
        if "parent directory" in anchor_text_lower or anchor_text_lower == "[to parent directory]": # Apache, Nginx, Lighttpd
            return True
        if anchor_text_lower == "../": # Simpler form
            if parent_dir_anchor.find_parent(['ul', 'ol', 'pre', 'table']): # Ensure it's part of a list-like structure
                return True

    # 3. Common header texts in tables or preformatted text (Apache, Nginx)
    common_headers_sets = [
        {"name", "last modified", "size"}, # Apache/Nginx
        {"to parent directory", "name", "size", "date modified"} # IIS
    ]
    header_elements_text = " ".join(elem.get_text().lower() for elem in soup.find_all(['th', 'h1', 'h2', 'h3', 'pre']))
    
    for header_set in common_headers_sets:
        if all(kw in header_elements_text for kw in header_set):
            return True
    if "<table>" in text_content_lower and "sort by" in text_content_lower and "name" in text_content_lower: # Another common pattern
        return True

    # 4. Heuristic: Count file-like links that are not navigational
    listing_links_count = 0
    distinct_hrefs = set()
    common_file_like_extensions = SENSITIVE_FILE_EXTENSIONS + [
        '.php', '.html', '.htm', '.js', '.css', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', 
        '.pdf', '.doc', '.xls', '.ppt', '.odt', '.ods', '.odp', '.swf', '.cgi', '.pl'
    ]

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        # Skip common non-listing links
        if href.startswith(('?', '#', 'javascript:', 'mailto:')) or href in ('../', './', '/'):
            continue
        
        parsed_href = urlparse(href)
        # Check if href is an absolute URL with a scheme and netloc
        is_href_absolute_and_different_host = bool(parsed_href.scheme and parsed_href.netloc) and \
                                              parsed_href.netloc != urlparse(url_path).netloc
        if is_href_absolute_and_different_host: # Different domain
            continue

        # Check if it looks like a file or directory
        is_dir_link = href.endswith('/')
        # More robust file check: has an extension, or filename contains a dot
        fname_part = href.split('/')[-1]
        is_file_link = any(fname_part.lower().endswith(ext) for ext in common_file_like_extensions) or \
                       ('.' in fname_part and not fname_part.startswith('.') and not fname_part.endswith('.'))

        if is_dir_link or is_file_link:
            # Avoid counting links that are clearly part of site navigation
            link_text = a_tag.get_text(strip=True).lower()
            common_nav_keywords = ["home", "about", "contact", "services", "product", "blog", "faq", "terms", "privacy", "login", "register", "sitemap", "documentation", "support", "download"]
            if any(nav_keyword in link_text for nav_keyword in common_nav_keywords) and len(link_text) < 25:
                # Check parent structure for common nav elements
                parent = a_tag.find_parent(['nav', 'footer', 'header'])
                if parent: continue
                parent_classes_ids = str(parent.attrs.get('class', []) + [parent.attrs.get('id', '')]).lower() if parent else ""
                if any(nav_clue in parent_classes_ids for nav_clue in ['nav', 'menu', 'footer', 'sidebar', 'breadcrumb', 'header', 'topbar']):
                    continue
            
            if href not in distinct_hrefs:
                listing_links_count += 1
                distinct_hrefs.add(href)

    if listing_links_count > 3: # Adjusted threshold
        return True
        
    # 5. IIS specific: often very plain, might just be a list of links inside <pre>
    pre_tags = soup.find_all('pre')
    for pre_tag in pre_tags:
        if len(pre_tag.find_all('a', href=True)) > 2 and "parent directory" in pre_tag.get_text().lower():
            return True # IIS often has "Parent Directory" in <pre>
        if len(pre_tag.find_all('a', href=True)) > 4: # Generic pre with many links
             return True

    # 6. Check for comments or meta tags indicating directory listing generation
    if "directory listing" in text_content_lower and ("generated by" in text_content_lower or "server at" in text_content_lower):
        return True
            
    return False

def _extract_links_from_listing(html_content, base_url):
    """Extracts file and directory links from a directory listing page."""
    links = {"dirs": [], "files": []}
    if not html_content:
        return links
    soup = BeautifulSoup(html_content, 'lxml')
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        
        # Skip parent directory, current directory, query string links, fragment links, javascript
        if href in ("../", "./") or href.startswith(("?", "#", "javascript:", "mailto:")):
            continue
        
        # Skip if it's an absolute URL to a different domain
        parsed_href = urlparse(href)
        # Check if href is an absolute URL with a scheme and netloc
        is_href_absolute_with_host = bool(parsed_href.scheme and parsed_href.netloc)
        if is_href_absolute_with_host and parsed_href.netloc != urlparse(base_url).netloc:
            continue

        # Resolve relative links against the current directory's URL
        full_url = urljoin(base_url, href)
        
        # Ensure we are still within the same path segment or deeper
        # This check is tricky with urljoin, focus on relative paths from listing
        if not full_url.startswith(base_url.rsplit('/', 1)[0] + '/'): # Ensure it's not going "too far up"
            # A simpler check: if href is an absolute URL and not starting with base_url, it's likely external or site root nav
            if is_href_absolute_with_host and not full_url.startswith(base_url):
                 # Allow if it's just a different path on the same host
                if urlparse(full_url).netloc != urlparse(base_url).netloc:
                    continue
        
        # Get the actual name of the file/directory from the href
        name = href.split('?')[0] # Remove query parameters from name

        if name.endswith('/'):
            links["dirs"].append(name.strip('/')) # Store dir name
        else:
            links["files"].append(name) # Store file name
    return links

def _fetch_and_analyze_file_content(file_url, config, state):
    """Fetches content of a given file URL and checks for sensitive patterns."""
    max_file_size = config.get('wp_analyzer', {}).get('dir_listing_max_file_size_fetch', DEFAULT_MAX_FILE_SIZE_TO_FETCH)
    analysis_result = {"url": file_url, "fetched": False, "contains_secrets": False, "patterns_found": [], "error": None, "size": 0}
    
    try:
        # Try HEAD request first to check size (if server supports it well)
        head_resp = make_request(file_url, config, method='HEAD', timeout=3, allow_redirects=True)
        if head_resp and 'content-length' in head_resp.headers:
            content_length = int(head_resp.headers['content-length'])
            analysis_result["size"] = content_length
            if content_length == 0: # Empty file
                analysis_result["error"] = "File is empty (0 bytes)."
                return analysis_result
            if content_length > max_file_size:
                analysis_result["error"] = f"File size ({content_length} bytes) exceeds fetch limit ({max_file_size} bytes)."
                return analysis_result
        
        response = make_request(file_url, config, method='GET', timeout=7, stream=True, allow_redirects=True)
        if response and response.status_code == 200:
            content_read = 0
            file_content_chunks = []
            for chunk in response.iter_content(chunk_size=1024): # Read in chunks
                if not chunk: # Skip empty chunks
                    continue
                if content_read + len(chunk) > max_file_size:
                    file_content_chunks.append(chunk[:max_file_size - content_read])
                    print(f"    [!] Truncated fetch for {file_url} as it exceeded max size during GET.")
                    content_read = max_file_size
                    break
                file_content_chunks.append(chunk)
                content_read += len(chunk)
            
            analysis_result["size"] = content_read # Actual read size
            if content_read == 0:
                analysis_result["error"] = "Fetched empty content."
                return analysis_result

            try:
                file_content = b"".join(file_content_chunks).decode('utf-8', errors='ignore')
            except UnicodeDecodeError: # Fallback for binary files or unexpected encodings
                file_content = b"".join(file_content_chunks).decode('latin-1', errors='ignore')

            analysis_result["fetched"] = True

            for pattern_name, regex_pattern in SENSITIVE_CONTENT_PATTERNS.items():
                # Using re.DOTALL for multiline patterns if needed, but most are single line
                # Using re.IGNORECASE for broader matching
                if re.search(regex_pattern, file_content, re.IGNORECASE | re.MULTILINE):
                    analysis_result["contains_secrets"] = True
                    analysis_result["patterns_found"].append(pattern_name)
            
            if analysis_result["contains_secrets"]:
                print(f"    [CRITICAL] Sensitive patterns ({', '.join(analysis_result['patterns_found'])}) found in {file_url}")
        elif response:
            analysis_result["error"] = f"HTTP status {response.status_code}"
        else: # No response object
            analysis_result["error"] = "Request failed (no response/timeout)"

    except Exception as e:
        analysis_result["error"] = str(e)
        print(f"    [-] Error fetching/analyzing file {file_url}: {e}")
    return analysis_result

def _check_and_log_listing(test_url, response, state, config, vulnerable_paths_map, base_scan_path_key, fetched_sensitive_files_details=None):
    """Helper to check response, log findings, and extract links if listing is found."""
    if response and response.status_code == 200:
        parsed_url = urlparse(test_url)
        if _is_directory_listing(response.text, parsed_url.path):
            print(f"    [!!!] Directory Listing ENABLED for: {test_url}")
            
            listed_content = _extract_links_from_listing(response.text, test_url)
            sensitive_files_summary_list = [] # For path_finding: [{'name': fname, 'reason': 'extension .log'}]

            for fname in listed_content["files"]:
                fname_lower = fname.lower()
                matched_ext = next((ext for ext in SENSITIVE_FILE_EXTENSIONS if fname_lower.endswith(ext)), None)
                if matched_ext:
                    sensitive_files_summary_list.append({'name': fname, 'reason': f"extension '{matched_ext}'", 'url': urljoin(test_url, fname)})
                    continue 

                matched_keyword = next((kw for kw in SENSITIVE_FILENAME_KEYWORDS if kw in fname_lower), None)
                if matched_keyword:
                    sensitive_files_summary_list.append({'name': fname, 'reason': f"keyword '{matched_keyword}'", 'url': urljoin(test_url, fname)})

            path_finding = {
                "url": test_url,
                "listed_dirs_count": len(listed_content["dirs"]),
                "listed_files_count": len(listed_content["files"]),
                "sensitive_files_identified": sensitive_files_summary_list, # More detailed
            }
            
            if fetched_sensitive_files_details: # Results from _fetch_and_analyze_file_content
                path_finding["fetched_sensitive_content_analysis"] = fetched_sensitive_files_details

            vulnerable_paths_map.setdefault(base_scan_path_key, [])
            # Avoid duplicate entries for the exact same URL under the same base_scan_path_key
            if not any(pf["url"] == test_url for pf in vulnerable_paths_map[base_scan_path_key]):
                 vulnerable_paths_map[base_scan_path_key].append(path_finding)

            severity = "Medium"
            description_extra = ""
            
            if sensitive_files_summary_list:
                severity = "High"
                summary_strings = [f"{d['name']} (reason: {d['reason']})" for d in sensitive_files_summary_list]
                description_extra = f" Sensitive files potentially exposed: {', '.join(summary_strings[:3])}{'...' if len(summary_strings)>3 else ''}."

            if fetched_sensitive_files_details and any(item.get('contains_secrets', False) for item in fetched_sensitive_files_details):
                severity = "Critical"
                critical_files = [item['url'] for item in fetched_sensitive_files_details if item.get('contains_secrets')]
                description_extra += f" CRITICAL: Sensitive data patterns found in fetched files (e.g., {critical_files[0] if critical_files else 'N/A'})."

            # Alert for each specific listing found
            state.add_critical_alert(f"Directory Listing: {test_url}" + (f" (Sensitive files: {len(sensitive_files_summary_list)}, Potential secrets: {severity=='Critical'})" if sensitive_files_summary_list or severity=='Critical' else ""))
            
            # Remediation is grouped by the base_scan_path_key
            remediation_key_suffix = sanitize_filename(base_scan_path_key.replace('/', '_').strip('_'))
            remediation_key = f"dir_listing_{remediation_key_suffix if remediation_key_suffix else 'root'}"
            
            if not state.remediation_exists(remediation_key) or state.get_remediation_severity(remediation_key) != "Critical":
                # Add or update if new severity is higher
                state.add_remediation_suggestion(remediation_key, {
                    "source": "WP Analyzer (Directory Listing - Enhanced)",
                    "description": f"Directory listing is enabled for paths under or including '{base_scan_path_key}'. Example vulnerable URL: {test_url}.{description_extra}",
                    "severity": severity,
                    "remediation": "Disable directory listing via web server configuration (e.g., 'Options -Indexes' in .htaccess for Apache, or 'autoindex off;' in Nginx). Ensure sensitive files are not publicly accessible and review any files flagged with 'CRITICAL' severity for exposed secrets."
                }, overwrite_lower_severity=True)
            return True, listed_content
    return False, None

def check_directory_listing(state, config, target_url):
    """Checks for directory listing enabled on common and discovered WordPress directories with enhancements."""
    wp_analyzer_module_key = "wp_analyzer"
    findings_subkey = "directory_listing_enhanced"

    analyzer_findings = state.get_module_findings(wp_analyzer_module_key, {})
    current_phase_findings = analyzer_findings.get(findings_subkey, {})
    if not current_phase_findings: # Initialize if not present
        current_phase_findings = {
            "status": "Starting",
            "vulnerable_paths_map": {}, # Keyed by base_scan_path_key
            "details": "Initializing enhanced directory listing checks..."
        }
    current_phase_findings["status"] = "Running"
    analyzer_findings[findings_subkey] = current_phase_findings
    state.update_module_findings(wp_analyzer_module_key, analyzer_findings) # Update state early

    print("    [i] Starting Enhanced Directory Listing Checks...")

    # Configurable options
    max_recursion_depth = config.get('wp_analyzer', {}).get('dir_listing_max_recursion', DEFAULT_MAX_RECURSION_DEPTH)
    fetch_sensitive_content = config.get('wp_analyzer', {}).get('dir_listing_fetch_sensitive_files', DEFAULT_FETCH_SENSITIVE_FILES)
    max_sensitive_to_fetch_per_dir = config.get('wp_analyzer', {}).get('dir_listing_max_sensitive_fetch', DEFAULT_MAX_SENSITIVE_FETCH_PER_DIR)

    # Expanded base directories to check
    base_dirs_to_check = list(set([ # Use set to ensure uniqueness
        "", # Check root path as well
        "wp-content/", "wp-content/uploads/", "wp-content/plugins/", "wp-content/themes/",
        "wp-content/mu-plugins/", "wp-content/upgrade/", "wp-content/languages/",
        "wp-includes/", "wp-includes/js/", "wp-includes/css/", "wp-includes/images/", "wp-includes/fonts/",
        "wp-admin/", "wp-admin/includes/", "wp-admin/css/", "wp-admin/js/", "wp-admin/images/", "wp-admin/maint/",
        "wp-content/backups/", "wp-content/backup/", "wp-content/cache/", "wp-content/logs/", "wp-content/debug/",
        "wp-content/tmp/", "wp-content/temp/", "wp-content/exports/", "wp-content/imports/", "wp-content/sessions/",
        "backups/", "backup/", "temp/", "tmp/", "logs/", "data/", "export/", "import/", "database/", "db_backups/",
        "includes/", "admin/", "assets/", "css/", "js/", "images/", "img/", "static/", "media/",
        "cgi-bin/", "vendor/", "node_modules/", ".git/", ".svn/", ".hg/", "storage/", "app/storage/"
    ]))
    
    # Add year/month paths for uploads dynamically for current and previous 2 years
    current_year = datetime.datetime.now().year
    for i in range(3): # Current year and previous two years
        year = str(current_year - i)
        base_dirs_to_check.append(f"wp-content/uploads/{year}/")
        for month in range(1, 13):
            base_dirs_to_check.append(f"wp-content/uploads/{year}/{month:02d}/")

    vulnerable_paths_map = current_phase_findings.get("vulnerable_paths_map", {})
    
    # Queue for iterative scanning: (url_to_check, base_scan_path_key, current_depth)
    # base_scan_path_key is the initial path from base_dirs_to_check that led to this scan, for grouping remediations.
    scan_queue = []
    for dir_path in base_dirs_to_check:
        scan_queue.append((urljoin(target_url, dir_path), dir_path, 0))
    
    processed_urls = set() # To avoid re-processing the same URL if added to queue multiple times

    while scan_queue:
        current_url, base_path_key, depth = scan_queue.pop(0)

        if current_url in processed_urls:
            continue
        processed_urls.add(current_url)

        print(f"    Checking [{depth}]: {current_url} (Base: {base_path_key})")
        try:
            response = make_request(current_url, config, timeout=7)
            
            fetched_content_details_for_log = None
            is_listing, listed_content = _check_and_log_listing(current_url, response, state, config, vulnerable_paths_map, base_path_key) # Initial check without content analysis

            if is_listing and listed_content:
                # If listing found, and content fetching is enabled, analyze some sensitive files
                if fetch_sensitive_content:
                    sensitive_files_to_fetch = [
                        item for item in vulnerable_paths_map.get(base_path_key, [])
                        if item["url"] == current_url # Find the finding for current_url
                    ]
                    if sensitive_files_to_fetch: # Should be one
                        current_url_finding = sensitive_files_to_fetch[0]
                        files_for_analysis = current_url_finding.get("sensitive_files_identified", [])
                        
                        fetched_content_details_for_log = []
                        fetched_count = 0
                        for sfile_info in files_for_analysis:
                            if fetched_count >= max_sensitive_to_fetch_per_dir:
                                break
                            file_to_analyze_url = sfile_info['url'] # URL is already resolved in sensitive_files_identified
                            print(f"      Fetching content for sensitive file: {file_to_analyze_url}")
                            analysis = _fetch_and_analyze_file_content(file_to_analyze_url, config, state)
                            fetched_content_details_for_log.append(analysis)
                            fetched_count += 1
                        
                        # Re-log with content analysis details if any secrets were found or attempted
                        if fetched_content_details_for_log:
                             # Remove previous finding for this URL to replace it with the more detailed one
                            vulnerable_paths_map[base_path_key] = [
                                pf for pf in vulnerable_paths_map[base_path_key] if pf["url"] != current_url
                            ]
                            _check_and_log_listing(current_url, response, state, config, vulnerable_paths_map, base_path_key, fetched_content_details_for_log)


                # Add subdirectories to queue if depth allows
                if depth < max_recursion_depth:
                    for sub_dir_name in listed_content.get("dirs", []):
                        # Ensure sub_dir_name doesn't create problematic URLs (e.g. "http:")
                        if ":" in sub_dir_name or sub_dir_name.startswith("//"): 
                            print(f"    [!] Skipping potentially malformed sub-directory name: {sub_dir_name} from {current_url}")
                            continue
                        
                        # Construct new URL carefully
                        # If current_url doesn't end with '/', urljoin might replace last segment
                        safe_current_url = current_url if current_url.endswith('/') else current_url + '/'
                        next_url = urljoin(safe_current_url, sub_dir_name + '/') # Ensure sub_dir also ends with / for urljoin
                        
                        if next_url not in processed_urls and next_url.startswith(target_url): # Stay within target
                            scan_queue.append((next_url, base_path_key, depth + 1))
            
        except Exception as e:
            print(f"    [-] Error checking directory {current_url}: {e}")
            state.add_error(f"Directory Listing check for {current_url} failed: {str(e)}")
        
        # Update state periodically or after each main path
        current_phase_findings["vulnerable_paths_map"] = vulnerable_paths_map
        analyzer_findings[findings_subkey] = current_phase_findings
        state.update_module_findings(wp_analyzer_module_key, analyzer_findings)


    total_vulnerable_unique_urls = sum(len(paths) for paths in vulnerable_paths_map.values())
    if total_vulnerable_unique_urls > 0:
        current_phase_findings["status"] = "Vulnerabilities Found"
        current_phase_findings["details"] = f"Found {total_vulnerable_unique_urls} unique URL(s) with directory listing. Check 'vulnerable_paths_map' for details. Some files may have been analyzed for sensitive content."
    else:
        current_phase_findings["status"] = "Completed (No Listings Found)"
        current_phase_findings["details"] = "No directory listings found on checked paths after enhanced scan."
    
    analyzer_findings[findings_subkey] = current_phase_findings # Final update
    state.update_module_findings(wp_analyzer_module_key, analyzer_findings)
    
    print(f"    [+] Enhanced Directory Listing checks finished. Status: {current_phase_findings['status']}")
