import re
from urllib.parse import urljoin, urlparse
import concurrent.futures # Added import
from core.utils import sanitize_filename # Core utils needed here
from .utils import make_request # Local utils for requests

def _parse_wp_config_content(content, source_url, state, module_key):
    """Helper function to parse potential wp-config content for sensitive info."""
    print(f"      Attempting to parse content from presumed wp-config backup: {source_url}")
    # Initialize structure for parsed details within the main findings dictionary
    analyzer_findings = state.get_module_findings(module_key, {})
    exposure_details = analyzer_findings.get("sensitive_file_exposure", {})
    if "parsed_config_files" not in exposure_details:
        exposure_details["parsed_config_files"] = []
    parsed_configs = exposure_details["parsed_config_files"]

    found_config_details = {"source_url": source_url, "parsed_items": {}}
    db_creds_found = False

    # Regex for define('KEY', 'VALUE'); - handles single and double quotes
    define_pattern = re.compile(r"define\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]*)['\"]\s*\)\s*;")
    # Regex for $table_prefix = 'VALUE';
    table_prefix_pattern = re.compile(r"\$table_prefix\s*=\s*['\"]([^'\"]+)['\"]\s*;")

    matches = define_pattern.findall(content)
    
    # Store actual credentials temporarily for command generation, but obfuscate for general reporting
    extracted_creds = {}

    # Extract table_prefix
    table_prefix_match = table_prefix_pattern.search(content)
    if table_prefix_match:
        found_config_details["parsed_items"]["TABLE_PREFIX"] = table_prefix_match.group(1)

    for key, value in matches:
        # List of sensitive keys to look for
        db_keys = ["DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST"]
        other_sensitive_keys = [
            "AUTH_KEY", "SECURE_AUTH_KEY", "LOGGED_IN_KEY", "NONCE_KEY",
            "AUTH_SALT", "SECURE_AUTH_SALT", "LOGGED_IN_SALT", "NONCE_SALT"
        ]
        
        if key in db_keys:
            extracted_creds[key] = value # Store actual value for potential command generation
            found_config_details["parsed_items"][key] = "********" if key == "DB_PASSWORD" else value
            db_creds_found = True
        elif key in other_sensitive_keys:
            found_config_details["parsed_items"][key] = "********" # Obfuscate salts and keys
            
        # Check for WP_DEBUG specifically
        if key == "WP_DEBUG" and value.lower() == "true":
            found_config_details["parsed_items"]["WP_DEBUG"] = "true"
            state.add_remediation_suggestion("wp_debug_enabled_config", {
                "source": "WP Analyzer",
                "description": f"WP_DEBUG is enabled in an exposed configuration file ({source_url}).",
                "severity": "Medium",
                "remediation": "Disable WP_DEBUG on production sites."
            })

    if db_creds_found:
        print("      [!!!] Database credentials potentially found in exposed config!")
        state.add_critical_alert(f"DB Credentials potentially found in exposed config: {source_url}")
        found_config_details["parsed_items"]["DB_CREDENTIALS_HINT"] = "Present (Details partially obfuscated in report)"
        
        # Add extracted (but not fully reported) creds to the specific config detail for this file
        # This is sensitive; ensure it's handled carefully and not broadly logged.
        found_config_details["_extracted_db_credentials"] = extracted_creds 

    # Append the parsed details to the list
    parsed_configs.append(found_config_details)
    exposure_details["parsed_config_files"] = parsed_configs
    analyzer_findings["sensitive_file_exposure"] = exposure_details
    state.update_module_findings(module_key, analyzer_findings)
    
    return extracted_creds if db_creds_found else None

SENSITIVE_KEYWORDS = [
    # Credentials & API Keys
    "password", "passwd", "secret", "apikey", "api_key", "auth_token", "access_token",
    "DB_PASSWORD", "FTP_PASSWORD", "MAIL_PASSWORD", "SMTP_PASSWORD",
    "private_key", "PRIVATE KEY", "client_secret", "bearer", "credential",
    # Configuration related
    "dsn", "connectionstring", "jdbc", "db_connect", "sqlnet.ora", "tnsnames.ora",
    # Specific service keys/tokens
    "aws_access_key_id", "aws_secret_access_key", "s3_key", "s3_secret",
    "slack_token", "github_token", "heroku_api_key", "stripe_key", "paypal_secret",
    # Backup / Internal structure
    "backup_password", "admin_pass", "root_password",
    # Crypto
    "BEGIN RSA PRIVATE KEY", "BEGIN DSA PRIVATE KEY", "BEGIN EC PRIVATE KEY", "BEGIN PGP PRIVATE KEY BLOCK",
    # Common vulnerable functions or misconfigurations (context dependent)
    "eval(", "exec(", "shell_exec(", "passthru(", "system(", "phpinfo" 
]

TEXT_MIME_TYPES_FOR_PARTIAL_SCAN = [
    "text/plain", "text/html", "text/xml", "application/xml", "application/json",
    "application/javascript", "application/x-javascript", "text/css",
    "application/sql", "text/x-sql",
    # Common log types, even if not strictly text/*
    "application/log", "text/log" 
]


def _scan_partial_content_for_keywords(content_chunk_bytes, keywords):
    """Scans a chunk of bytes (decoded as text) for sensitive keywords."""
    found_keywords = set()
    try:
        # Try decoding with UTF-8, then fall back to latin-1 if errors occur
        try:
            content_chunk_text = content_chunk_bytes.decode('utf-8')
        except UnicodeDecodeError:
            content_chunk_text = content_chunk_bytes.decode('latin-1', errors='replace')
        
        content_lower = content_chunk_text.lower() # Search case-insensitively for most keywords

        for keyword in keywords:
            # Some keywords are case-sensitive (like "BEGIN RSA PRIVATE KEY")
            if keyword.isupper() or any(c.isupper() for c in keyword if c.isalpha()): # Mix of case or all upper
                if keyword in content_chunk_text:
                    found_keywords.add(keyword)
            else: # Default to case-insensitive
                if keyword.lower() in content_lower:
                    found_keywords.add(keyword)
                    
    except Exception as e:
        print(f"        Error during keyword scanning: {e}")
    return list(found_keywords)

# Common file signatures (magic bytes)
# Key: lowercase extension (with dot), Value: list of possible byte sequences
FILE_SIGNATURES = {
    ".zip": [b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"], # ZIP archive
    ".gz": [b"\x1f\x8b\x08"],                             # Gzip compressed file
    ".rar": [b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01\x00"], # RAR archive (RAR 1.5-4.x and RAR 5.0+)
    ".tar": [b"ustar"],                                  # TAR archive (often found at offset 257, but checking start for simplicity here or as part of .tar.gz)
    ".pdf": [b"%PDF-"],                                  # PDF document
    ".png": [b"\x89PNG\r\n\x1a\n"],                      # PNG image
    ".jpg": [b"\xff\xd8\xff"],                           # JPEG image (common SOI marker)
    ".jpeg": [b"\xff\xd8\xff"],                          # JPEG image
    ".sql": [b"CREATE TABLE", b"INSERT INTO", b"DROP TABLE", b"DATABASE", b"DEFAULT CHARACTER SET", b"-- ", b"/*"], # Common SQL keywords (UTF-8 encoded)
    ".php": [b"<?php", b"<?=", b"<script language=\"php\">"], # PHP scripts
    ".sh": [b"#!/bin/sh", b"#!/bin/bash"],                # Shell scripts
    ".py": [b"#!/usr/bin/python", b"#!/usr/bin/env python"], # Python scripts
    # Add more as needed, e.g., for .7z, .bz2, etc.
}

def _verify_file_signature(file_content_bytes, file_name_or_extension):
    """
    Verifies file signature based on its content and expected extension.
    Returns: True (match), False (mismatch), None (unknown/not checked).
    """
    normalized_extension = ""
    if "." in file_name_or_extension:
        normalized_extension = "." + file_name_or_extension.split('.')[-1].lower()
    
    if not normalized_extension or normalized_extension not in FILE_SIGNATURES:
        # If extension is not in our list, or no clear extension, we can't verify.
        # Could also try to guess from content if desired, but that's more complex.
        return None 

    expected_signatures = FILE_SIGNATURES[normalized_extension]
    
    for sig in expected_signatures:
        # For text-based signatures (like SQL, PHP), decode content part for check
        if normalized_extension in [".sql", ".php", ".sh", ".py"]: # Files likely to be text
            try:
                # Try decoding a small chunk for text signature checks
                chunk_to_check = file_content_bytes[:max(len(sig) + 20, 1024)].decode('utf-8', errors='ignore')
                if sig.decode('utf-8', errors='ignore') in chunk_to_check: # Check if sig (as string) is in decoded chunk
                    return True
            except Exception:
                pass # Ignore decoding errors for this simple check
        elif file_content_bytes.startswith(sig): # For binary signatures
            return True
            
    # Special case for .tar files, signature is often at offset 257
    if normalized_extension == ".tar":
        if len(file_content_bytes) > 261 and file_content_bytes[257:257+5] == b"ustar":
            return True

    return False # No signature matched


from datetime import datetime, timedelta

def _generate_date_pattern_backups(base_names, extensions, date_formats, years_depth=2):
    """Generates backup filenames with date patterns."""
    dated_filenames = set()
    today = datetime.now()
    # Generate for recent N years, current month, last month, specific days
    dates_to_try = []

    for year_delta in range(years_depth + 1): # Current year and N previous years
        year = today.year - year_delta
        # Full year backups
        dates_to_try.append(datetime(year, 1, 1)) # Placeholder for YYYY pattern part

        # Monthly for current and previous year
        if year_delta <= 1:
            for month in range(1, 13):
                try:
                    dates_to_try.append(datetime(year, month, 1))
                except ValueError: # Handles cases like Feb 29 on non-leap year if day was fixed
                    pass
        
        # Daily for last N days (e.g., 7 days) for current year
        if year_delta == 0:
            for day_delta in range(7): # Last 7 days
                dates_to_try.append(today - timedelta(days=day_delta))

    # Unique dates
    unique_dates = sorted(list(set(d.date() for d in dates_to_try if isinstance(d, datetime))), reverse=True)
    # Add year-only placeholders for patterns like backup_YYYY.zip
    year_placeholders = sorted(list(set(d.year for d in dates_to_try if isinstance(d, datetime))), reverse=True)


    for base in base_names:
        for ext in extensions:
            for dt_obj_date in unique_dates:
                for fmt_str in date_formats: # e.g., "%Y-%m-%d", "%Y%m%d", etc.
                    try:
                        date_str = dt_obj_date.strftime(fmt_str)
                        dated_filenames.add(f"{base}{date_str}{ext}")
                        dated_filenames.add(f"{base}_{date_str}{ext}")
                        dated_filenames.add(f"{base}-{date_str}{ext}")
                    except ValueError: # Should not happen if dt_obj_date is a date object
                        pass
            for year_val in year_placeholders:
                 # For patterns like backup_YYYY.zip or backup-YYYY.zip
                 dated_filenames.add(f"{base}{year_val}{ext}")
                 dated_filenames.add(f"{base}_{year_val}{ext}")
                 dated_filenames.add(f"{base}-{year_val}{ext}")


    # Add patterns with common timestamp formats (less common for manual backups but seen)
    # Example: backup_YYYYMMDD-HHMMSS.zip - this can be very noisy, use sparingly or make more configurable
    # For now, focusing on date-based patterns.

    return dated_filenames


def check_sensitive_file_exposure(state, config, target_url):
    """Checks for publicly accessible sensitive files."""
    module_key = "wp_analyzer"
    scan_level = config.get("file_exposure_scan_level", "moderate").lower() # light, moderate, deep
    analyzer_findings = state.get_module_findings(module_key, {})
    # Ensure the specific key exists before trying to access sub-keys
    if "sensitive_file_exposure" not in analyzer_findings:
        analyzer_findings["sensitive_file_exposure"] = {"status": "Running", "found_files": []}
    exposure_details = analyzer_findings["sensitive_file_exposure"]

    # Expanded list of sensitive files and backup patterns
    base_sensitive_files = [
        # Config files
        "wp-config.php", "config.php",
        # Logs
        "debug.log", "error.log", "php_error.log", "error_log", "php_errors.log", "access.log", "access_log",
        # Environment files
        ".env",
        # Database dumps
        "dump.sql", "backup.sql", "db.sql", "database.sql", "site.sql", "wordpress.sql", "data.sql", "export.sql", "wp_backup.sql",
        # PHP config/info
        "php.ini", ".user.ini", "phpinfo.php", "info.php", "test.php", "phpversion.php",
        # Common archive formats (generic names)
        "backup", "site", "wordpress", "wp", "files", "archive", "data_backup",
        # Version control system files/dirs (common ones to check for exposure)
        ".git/config", ".git/HEAD", ".git/index", ".svn/wc.db", ".svn/entries",
        # Dependency management files
        "composer.json", "composer.lock", "package.json", "yarn.lock", "package-lock.json",
        # Server config files
        ".htaccess", ".htaccess.bak", ".htaccess.old", "web.config",
        # Common backup plugin paths (examples, can be expanded)
        "wp-content/uploads/backup-guard/", # Backup Guard plugin
        "wp-content/backups/", # Common generic backup dir
        "wp-content/ai1wm-backups/", # All-in-One WP Migration
        "wp-content/updraft/", # UpdraftPlus
        "wp-content/wpvividbackups/", # WPvivid
        # Other potentially sensitive files
        "security.txt", # /.well-known/security.txt is standard, but check root too
        "readme.html", # WordPress readme, can reveal version
        "license.txt", # WordPress license, less sensitive but sometimes checked
        "wp-cron.php", # Can be hit directly, though not usually a file exposure vuln
        "xmlrpc.php" # Often checked, though more about its functionality
    ]

    backup_suffixes = [
        ".bak", ".old", ".save", ".swp", ".txt", ".zip", ".tar.gz", ".tgz", ".rar", ".7z",
        "~", "_backup", "_old", "_dev", "_live", "_prod", "_test", ".sql.zip", ".sql.gz",
        ".bak.zip", ".bak.gz", ".old.zip", ".old.gz", ".1", ".2", ".orig"
    ]
    
    archive_extensions = [".zip", ".tar.gz", ".tgz", ".rar", ".7z", ".tar"]

    sensitive_files_to_check = set()

    if scan_level == "light":
        # Minimal set for light scan
        light_bases = ["wp-config.php", "debug.log", ".env", "backup.zip", "dump.sql"]
        light_suffixes = [".bak", ".old", ".zip", ".sql"]
        sensitive_files_to_check.update(light_bases)
        for f_name in light_bases:
            for suffix in light_suffixes:
                if not f_name.endswith(suffix): # Avoid wp-config.php.sql etc. if base already has common type
                     sensitive_files_to_check.add(f_name + suffix)
        sensitive_files_to_check.add(".git/config") # Still important
        sensitive_files_to_check.add(".htaccess")
    
    if scan_level == "moderate" or scan_level == "deep":
        sensitive_files_to_check.update(base_sensitive_files)
        # Generate variations for config and common files
        config_like_files = ["wp-config.php", "config.php", ".env", "php.ini", ".user.ini", ".htaccess", "web.config"]
        for f_name in config_like_files:
            for suffix in backup_suffixes:
                sensitive_files_to_check.add(f_name + suffix)

        # Generate variations for generic archive names
        generic_archive_bases_moderate = ["backup", "site", "wordpress", "wp", "files", "database", "db_backup", "full_backup", urlparse(target_url).netloc] # Add domain name as base
        for base_name in generic_archive_bases_moderate:
            for ext in archive_extensions:
                sensitive_files_to_check.add(base_name + ext)
                for suffix in ["_current", "_latest", "_old", "_1", "_2", "_new", "_temp"]: 
                     sensitive_files_to_check.add(base_name + suffix + ext)
    
    if scan_level == "deep":
        print("    [Deep Scan Mode] Generating date-patterned backup filenames...")
        # Date patterns for deep scan
        date_pattern_bases = ["backup", "site", "wordpress", "wp", "database", urlparse(target_url).netloc]
        date_formats_to_try = ["%Y-%m-%d", "%Y%m%d", "%d-%m-%Y", "%m-%d-%Y", "%Y_%m_%d"]
        # Consider fewer years for less noise, or make years_depth configurable
        years_to_check_deep = config.get("file_exposure_deep_scan_years", 1) 
        
        dated_backups = _generate_date_pattern_backups(date_pattern_bases, archive_extensions, date_formats_to_try, years_depth=years_to_check_deep)
        sensitive_files_to_check.update(dated_backups)
        print(f"    Added {len(dated_backups)} date-patterned filenames for deep scan.")

    if not sensitive_files_to_check: # Fallback if scan_level is invalid
        print("    [Warning] Invalid scan_level, defaulting to moderate file list generation.")
        sensitive_files_to_check.update(base_sensitive_files) # Default to moderate if level is unknown
        # (Could re-run moderate generation here if it wasn't already done)


    base_parsed_url = urlparse(target_url)
    # Ensure found_files list exists
    if "found_files" not in exposure_details:
        exposure_details["found_files"] = []
    found_files_list = exposure_details["found_files"]

    # Define common WordPress directories to check files in
    wp_core_dirs = ["", "wp-admin/", "wp-includes/", "wp-content/"] # Root, admin, includes, content
    # Specific directories where backups or sensitive files might be misplaced
    wp_common_subdirs = [
        "wp-content/uploads/", 
        "wp-content/backups/", # Generic backup dir
        "wp-content/plugins/", # Less common for direct file exposure, but check for stray zips/configs
        "wp-content/themes/",
        "wp-content/upgrade/",
        "wp-content/cache/", # Sometimes logs or temp files
        "logs/", # Common log directory at root
        "temp/", "tmp/" # Common temp directories at root
    ]

    # Create a comprehensive list of (file_path, potential_dir_prefix) tuples
    # This helps manage where each file is checked.
    files_and_locations_to_test = []

    for file_path_template in sensitive_files_to_check:
        # Files that are typically at the root or have their full path specified
        if "/" in file_path_template or file_path_template.startswith("."):
            files_and_locations_to_test.append((file_path_template, "")) # Check at root
            if file_path_template == "debug.log": # Special handling for debug.log
                 files_and_locations_to_test.append((file_path_template, "wp-content/"))
        else:
            # For files without a path, check in common WP directories
            for core_dir in wp_core_dirs:
                files_and_locations_to_test.append((file_path_template, core_dir))
            # Also check some specific files in common subdirectories
            if any(archive_ext in file_path_template for archive_ext in archive_extensions) or \
               any(sql_ext in file_path_template for sql_ext in [".sql", ".sql.gz", ".sql.zip"]):
                for sub_dir in ["wp-content/uploads/", "wp-content/backups/", "wp-content/upgrade/"]:
                    files_and_locations_to_test.append((file_path_template, sub_dir))
    
    # Add specific checks for common backup plugin paths if not already covered
    # These are full paths, so they go directly.
    specific_plugin_backup_paths = [
        "wp-content/uploads/backup-guard/backup.zip", # Example, specific file names vary
        "wp-content/ai1wm-backups/site.wpress", # All-in-One WP Migration
        # Add more known default backup names/paths for popular plugins
    ]
    for pbp in specific_plugin_backup_paths:
        files_and_locations_to_test.append((pbp, ""))


    # Deduplicate and construct full URLs
    # Store (file_name_for_reporting, url_to_check) tuples
    urls_to_check_map = {} 

    for file_name, dir_prefix in files_and_locations_to_test:
        full_path = f"{dir_prefix}{file_name}".replace("//", "/")
        test_url = urljoin(target_url, full_path)
        if test_url not in urls_to_check_map:
            urls_to_check_map[test_url] = file_name # Store original pattern

    processed_url_count = 0
    total_urls_to_check = len(urls_to_check_map)
    print(f"  [i] Will check {total_urls_to_check} unique URLs for sensitive file exposure.")

    # Concurrency settings
    max_workers = config.get("file_exposure_concurrency", 10)
    # Ensure max_workers is at least 1
    max_workers = max(1, int(max_workers))
    
    # List to store results from threads
    # Each item will be a dictionary if a file is found, or None
    thread_results = []

    # Worker function to check a single URL
    def _worker_check_url(url_to_check, original_file_pattern):
        nonlocal processed_url_count # To update counter from threads (use with caution or pass counter if needed)
        
        max_file_size_to_get = config.get("file_exposure_max_size_kb", 5120) * 1024
        partial_get_size = config.get("file_exposure_partial_get_kb", 256) * 1024
        
        # This print can be noisy with many threads, consider conditional print or logging
        # print(f"    Checking (Thread): {url_to_check} (for: {original_file_pattern})")
        
        head_response = make_request(url_to_check, config, method="HEAD", allow_redirects=True)
        result_details = None # Initialize result for this URL

        if head_response and head_response.status_code == 200:
            content_type_head = head_response.headers.get("Content-Type", "").lower()
            content_disp_head = head_response.headers.get("Content-Disposition", "").lower()
            content_length_head_str = head_response.headers.get("Content-Length")
            content_length_head = int(content_length_head_str) if content_length_head_str and content_length_head_str.isdigit() else None

            if "text/html" in content_type_head and (content_length_head is not None and content_length_head < 200):
                return None # Likely error page, skip

            if content_length_head is not None and content_length_head > max_file_size_to_get:
                result_details = {
                    "type": "large_file_head",
                    "url": url_to_check, "status_code": head_response.status_code, "content_type": content_type_head,
                    "content_disposition": content_disp_head, "size": content_length_head,
                    "original_file_pattern": original_file_pattern,
                    "note": f"File is very large ({content_length_head} bytes). Full content not downloaded. Review manually.",
                    "keywords_in_partial_content": []
                }
                # Attempt partial GET for keyword scan on large files
                is_text_based_for_scan = any(mime_type in content_type_head for mime_type in TEXT_MIME_TYPES_FOR_PARTIAL_SCAN) or \
                                         any(original_file_pattern.lower().endswith(ext) for ext in ['.log', '.txt', '.sql', '.json', '.xml', '.yaml', '.ini', '.conf', '.config', '.php', '.js', '.html', '.env'])
                if is_text_based_for_scan and partial_get_size > 0:
                    partial_headers = {'Range': f'bytes=0-{partial_get_size-1}'}
                    partial_response = make_request(url_to_check, config, method="GET", headers=partial_headers)
                    if partial_response and partial_response.status_code in [200, 206]:
                        keywords = _scan_partial_content_for_keywords(partial_response.content, SENSITIVE_KEYWORDS)
                        if keywords:
                            result_details["keywords_in_partial_content"] = keywords
                            result_details["note"] += f" Keywords found in first {partial_get_size // 1024}KB: {', '.join(keywords)}."
                return result_details

            # Proceed with GET if HEAD was OK and size is manageable
            response = make_request(url_to_check, config, method="GET")
            if response and response.status_code == 200:
                content_type = response.headers.get("Content-Type", content_type_head).lower()
                content_disp = response.headers.get("Content-Disposition", content_disp_head).lower()
                actual_size = len(response.content)

                is_likely_html_error_page = "text/html" in content_type and (
                    any(kw in response.text.lower() for kw in [
                        "error", "not found", "page not found", "forbidden", "access denied",
                        "<!doctype html>", "<html>", "<head>", "<body>", "redirecting",
                        "server error", "oops!", "something went wrong"
                    ]) or actual_size < 200)
                
                is_archive_type = any(ext in original_file_pattern for ext in archive_extensions + [".sql", ".log", ".ini", ".json", ".lock", ".txt"]) or \
                                    any(cd_type in content_disp for cd_type in ["attachment", "application/octet-stream"]) or \
                                    any(ct_type in content_type for ct_type in ["application/zip", "application/x-gzip", "application/x-tar", "application/octet-stream", "text/plain", "application/sql"])
                
                plausible_size = actual_size > 10
                if "text/html" in content_type and not is_archive_type: plausible_size = actual_size > 500

                if not is_likely_html_error_page and plausible_size:
                    signature_match_status = _verify_file_signature(response.content, original_file_pattern)
                    result_details = {
                        "type": "exposed_file_get",
                        "url": url_to_check, "status_code": response.status_code, "content_type": content_type,
                        "content_disposition": content_disp, "size": actual_size,
                        "original_file_pattern": original_file_pattern,
                        "signature_verification": signature_match_status,
                        "content_for_parsing": response.text if "wp-config" in original_file_pattern.lower() else None # Only pass content if it's wp-config
                    }
                    if signature_match_status is False:
                        result_details["note"] = "File signature MISMATCH for expected type."
                    elif signature_match_status is True:
                        result_details["note"] = "File signature MATCHES expected type."
                    return result_details
        return None # No exposure found or error during HEAD

    # Use ThreadPoolExecutor for concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(_worker_check_url, url, pattern): url for url, pattern in urls_to_check_map.items()}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            processed_url_count += 1
            if processed_url_count % 100 == 0 or processed_url_count == total_urls_to_check : # Print progress
                 print(f"    Checked {processed_url_count}/{total_urls_to_check} URLs for file exposure...")
            try:
                result = future.result()
                if result:
                    thread_results.append(result)
            except Exception as exc:
                print(f"    Exception for {url}: {exc}")

    # Process results from threads in the main thread
    for result_data in thread_results:
        if not result_data: continue

        original_file_name_for_reporting = result_data["original_file_pattern"]
        test_url = result_data["url"]
        
        # Common details for reporting
        report_details = {
            "url": test_url, "status_code": result_data["status_code"], 
            "content_type": result_data["content_type"],
            "content_disposition": result_data["content_disposition"], 
            "size": result_data["size"],
            "original_file_pattern": original_file_name_for_reporting,
            "note": result_data.get("note", "")
        }
        if "keywords_in_partial_content" in result_data and result_data["keywords_in_partial_content"]:
            report_details["keywords_in_partial_content"] = result_data["keywords_in_partial_content"]
        if "signature_verification" in result_data:
            report_details["signature_verification"] = result_data["signature_verification"]


        # Determine severity (can be refined)
        severity = "Low" # Default
        file_path_lower = original_file_name_for_reporting.lower()
        if "wp-config" in file_path_lower or ".sql" in file_path_lower or ".env" in file_path_lower: severity = "High"
        elif ".git/config" in file_path_lower or ".svn/wc.db" in file_path_lower: severity = "High"
        elif "debug.log" in file_path_lower or "error.log" in file_path_lower or "php_error" in file_path_lower: severity = "Medium"
        elif ".log" in file_path_lower: severity = "Low"
        elif ".ini" in file_path_lower or "phpinfo.php" in file_path_lower: severity = "Medium"
        elif any(ext in file_path_lower for ext in archive_extensions):
            severity = "Medium"
            if "backup" in file_path_lower or "dump" in file_path_lower or "site" in file_path_lower or "wordpress" in file_path_lower:
                severity = "High"
        
        if result_data["type"] == "large_file_head":
            print(f"    [!!!] LARGE SENSITIVE FILE DETECTED (via HEAD): {test_url} (Size: {result_data['size']} bytes)")
            if not any(d["url"] == test_url for d in found_files_list):
                found_files_list.append(report_details)
            state.add_critical_alert(f"Large Sensitive File Exposed ({severity}): {test_url}, Size: {result_data['size']}")
            state.add_remediation_suggestion(f"large_file_expose_{sanitize_filename(original_file_name_for_reporting)}", {
                "source": "WP Analyzer",
                "description": f"Potentially sensitive LARGE file '{original_file_name_for_reporting}' (Size: {result_data['size']} bytes) found at {test_url}. Full content not fetched. Manual review required.",
                "severity": severity, "remediation": "Secure or remove the large publicly accessible file."
            })
            if result_data.get("keywords_in_partial_content"):
                 state.add_critical_alert(f"Keywords found in partial content of Large Sensitive File ({severity}): {test_url}, Keywords: {', '.join(result_data['keywords_in_partial_content'])}")


        elif result_data["type"] == "exposed_file_get":
            print(f"    [!!!] POTENTIALLY SENSITIVE FILE EXPOSED (via GET): {test_url}")
            if not any(d["url"] == test_url for d in found_files_list):
                found_files_list.append(report_details)
            
            state.add_critical_alert(f"Sensitive File Exposed ({severity}): {test_url} (matched pattern: {original_file_name_for_reporting})")
            state.add_remediation_suggestion(f"file_expose_{sanitize_filename(original_file_name_for_reporting)}_{sanitize_filename(test_url.replace(target_url, ''))}", {
                "source": "WP Analyzer",
                "description": f"Potentially sensitive file matching pattern '{original_file_name_for_reporting}' found at {test_url}. Content should be reviewed manually.",
                "severity": severity,
                "remediation": "Remove publicly accessible sensitive files. Ensure proper server permissions and web server rules."
            })

            if "wp-config" in file_path_lower and result_data.get("content_for_parsing"):
                extracted_db_creds = _parse_wp_config_content(result_data["content_for_parsing"], test_url, state, module_key)
                if extracted_db_creds:
                    mysql_available = state.get_full_state().get("tool_checks", {}).get("mysql", {}).get("status") == "Found"
                    db_name = extracted_db_creds.get("DB_NAME")
                    db_user = extracted_db_creds.get("DB_USER")
                    db_pass = extracted_db_creds.get("DB_PASSWORD")
                    db_host = extracted_db_creds.get("DB_HOST", "localhost")
                    
                    # Find the table_prefix from the already updated state by _parse_wp_config_content
                    current_parsed_configs = state.get_module_findings(module_key, {}).get("sensitive_file_exposure", {}).get("parsed_config_files", [])
                    table_prefix = "wp_" # default
                    for cfg in reversed(current_parsed_configs): # Check most recent first
                        if cfg.get("source_url") == test_url:
                            table_prefix = cfg.get("parsed_items", {}).get("TABLE_PREFIX", "wp_")
                            break
                    
                    if db_name and db_user and db_pass:
                        for item in found_files_list:
                            if item["url"] == test_url:
                                item["actionable_info"] = item.get("actionable_info", {})
                                item["actionable_info"]["db_credentials_extracted"] = {"db_name": db_name, "db_user": db_user, "db_host": db_host, "table_prefix": table_prefix}
                                if mysql_available:
                                    mysql_command_suggestion = f"mysql -h \"{db_host}\" -u \"{db_user}\" -p'{db_pass}' \"{db_name}\" -e \"SHOW TABLES; SELECT COUNT(*) FROM {table_prefix}users;\""
                                    suggestion_text = (
                                        f"Extracted DB credentials. Try connecting (USE WITH EXTREME CAUTION - exposes password in command history if not handled carefully):\n"
                                        f"    Host: {db_host}, User: {db_user}, DB: {db_name}, Prefix: {table_prefix}\n"
                                        f"    Example command (password included, BEWARE of shell history):\n"
                                        f"    {mysql_command_suggestion}\n"
                                        f"    Alternatively, use interactive prompt: mysql -h \"{db_host}\" -u \"{db_user}\" -p \"{db_name}\" (then enter password)\n"
                                        f"    (Ensure 'mysql' client is installed. Consider using MYSQL_PWD environment variable for the password to avoid shell history issues if scripting.)"
                                    )
                                    item["actionable_info"]["suggested_db_connect_command"] = suggestion_text
                                    item["actionable_info"]["extracted_db_password_NOTE"] = "Password was extracted and IS included in one of the suggested commands above. Handle with extreme care due to shell history risks."
                                    print(f"        [ACTIONABLE] {suggestion_text}")
                                    state.add_remediation_suggestion(f"db_creds_exposed_connect_{sanitize_filename(original_file_name_for_reporting)}", {
                                        "source": "WP Analyzer (File Exposure)",
                                        "description": f"Database credentials found in {test_url}. Suggested manual connection command provided. IMMEDIATE ATTENTION REQUIRED.",
                                        "severity": "Critical",
                                        "remediation": f"Immediately secure or remove the exposed file ({test_url}). Change database credentials. Investigate potential unauthorized access. Review web server configurations to prevent access to sensitive files."
                                    })
                                else:
                                    item["actionable_info"]["db_connection_note"] = "MySQL client not detected by tool checker; manual connection attempt may still be possible using extracted credentials."
                                break
    
    exposure_details["found_files"] = found_files_list
    exposure_details["status"] = "Checked"
    analyzer_findings["sensitive_file_exposure"] = exposure_details
    state.update_module_findings(module_key, analyzer_findings)
