# =============================================================================
# JS File Downloader & Archiver
# -----------------------------------------------------------------------------
# This tool downloads and archives JavaScript files (both external and inline)
# from a target URL using Playwright. It supports filtering out common libraries
# and analytics scripts, deduplication, crawling internal links, and advanced
# output management. Useful for security research, web archiving, and analysis.
# =============================================================================

#!/usr/bin/env python3
# --------------------------
# Imports
# --------------------------
import asyncio
import re
import argparse
import hashlib
import logging
import shutil
from pathlib import Path
from urllib.parse import urlparse, urljoin
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import validators
from urllib.parse import urlparse, urlunparse

# ============================= FILTERING LISTS =============================
# Patterns for filtering out "uninteresting" JavaScript files (e.g., analytics, libraries)
UNINTERESTING_JS_STRICT = [
    r'segment\\.com', r'google-analytics\\.com', r'googletagmanager\\.com',
    r'facebook\\.net', r'twitter\\.com', r'linkedin\\.com', r'hotjar\\.com',
    r'jquery(?:\\.min)?\\.js', r'bootstrap(?:\\.min)?\\.js', r'cdn\\.jsdelivr\\.net',
    r'cdn\\.cloudflare\\.com', r'polyfill\\.io', r'ads?\\.', r'track(?:ing)?\\.js',
    r'analytics\\.js', r'gtm\\.js', r'optimizely\\.com', r'\\.min\\.js$',
    r'webpack', r'react', r'vue', r'angular', r'\/vendor\/', r'\/plugins\/',
    r'\/docs\/', r'\/themes\/', r'\/dist\/',
    r'\\.(?:woff|woff2|ttf|ttc|otf|eot|svg|png|jpg|js)$'
]

UNINTERESTING_JS_RELAXED = [
    r'segment\\.com', r'google-analytics\\.com', r'googletagmanager',
    r'facebook\\.com', r'twitter\\.com', r'linkedin\\.com',
    r'hotspot|hotjar',
    r'jquery(?:\\.com$|\\.js)', r'bootstrap(?:\\.js)', r'cdn\\.js\\.',
    r'cloudflare\\.com', r'polyfill\\.io', r'ads?\\.', r'track(?:ing)?\\.js',
    r'analytics\\.js', r'gtm\\.js', r'optimizely\\.com',
    r'webpack', r'react', r'vue', r'angular',
    r'\\.(?:woff|woff2|ttf|eot|svg|png|jpg)\\.js$'
]

# ============================= LOGGER SETUP =============================
# Configure logging for info and debug output
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
log = logging.getLogger(__name__)

# ============================= HELPER FUNCTIONS =============================

def is_interesting_js(url: str, uninteresting_patterns) -> bool:
    """
    Returns True if the JS file URL does not match any uninteresting patterns.
    Used to filter out common libraries and analytics scripts.
    """
    lower_url = url.lower()
    return not any(re.search(pattern, lower_url) for pattern in uninteresting_patterns)

def is_interesting_inline_script(content: str, uninteresting_patterns) -> bool:
    """
    Returns True if the inline script content does not match any uninteresting patterns.
    Used to filter out uninteresting inline scripts.
    """
    lower_content = content.lower()
    return not any(re.search(pattern, lower_content) for pattern in uninteresting_patterns)

def sanitize_filename_part(text: str) -> str:
    """
    Sanitizes a string to be used as part of a filename.
    Replaces forbidden characters and trims underscores.
    """
    # Replace only forbidden filename characters, keep underscores and dashes
    text = re.sub(r'[<>:"/\\|?*\']', '_', text)
    text = re.sub(r'_+', '_', text)
    return text.strip('_')

def build_filename(url: str, content: bytes) -> str:
    """
    Builds a unique filename for a JS file based on its URL and content hash.
    Ensures filename is safe and not too long for the filesystem.
    """
    parsed = urlparse(url)
    host = sanitize_filename_part(parsed.netloc)
    # Remove leading slash and extension from path, keep as much as possible
    path = parsed.path.lstrip('/')
    if path.endswith('.js'):
        path = path[:-3]
    path = sanitize_filename_part(path)
    hash_prefix = hashlib.sha256(content).hexdigest()[:8]
    filename = f"{host}_{path}_{hash_prefix}.js"
    # Truncate only if filename is too long for Windows (max 255 chars)
    return filename

def get_domain_from_url(url: str) -> str:
    """
    Extracts the domain from a URL.
    Used for organizing output directories and filtering.
    """
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    return domain.lower()

async def extract_inline_scripts(page):
    """
    Extracts all inline <script> tags from the page's HTML.
    Returns a list of script contents.
    """
    try:
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        return [script.text for script in soup.find_all('script') if script.text]
    except Exception as e:
        log.warning(f"⚠️ Failed to extract inline scripts: {e}")
        return []

async def setup_browser():
    """
    Launches a headless Chromium browser using Playwright and returns the browser context and page.
    Sets user agent and viewport for more realistic browsing.
    """
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        viewport={"width": 1366, "height": 768}
    )
    page = await context.new_page()
    return playwright, browser, context, page

def collect_js_urls(page, output_dir, hash_set, uninteresting_patterns, include_cross_origin, min_size, verbose, skipped_counters, domain):
    """
    Registers a Playwright event handler to collect and save interesting JS files as they are loaded.
    Handles deduplication, filtering, and file saving.
    """
    async def on_response(response):
        # Only process script, fetch, or xhr resources
        if response.request.resource_type in ["script", "fetch", "xhr"]:
            url = response.url
            url_domain = get_domain_from_url(url)
            # Check if cross-origin is allowed or if the domain matches
            if (include_cross_origin or url_domain == domain) and is_interesting_js(url, uninteresting_patterns):
                try:
                    content = await response.body()
                    if len(content) < min_size:
                        log.debug(f"⚠️ Skipping small file: {url}")
                        skipped_counters['small'] += 1
                        return
                    content_hash = hashlib.sha256(content).hexdigest()
                    if content_hash in hash_set:
                        log.debug(f"⚠️ Skipping duplicate file: {url}")
                        skipped_counters['duplicate'] += 1
                        return
                    hash_set.add(content_hash)
                    filename = build_filename(url, content)
                    filepath = output_dir / filename
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    if verbose:
                        log.debug(f"💾 Saved: {filename} ({url})")
                except Exception as e:
                    log.error(f"❌ Error downloading {url}: {str(e)}")

    # Register the event handler for each response
    page.on("response", lambda response: asyncio.create_task(on_response(response)))
    
async def process_inline_scripts(inline_scripts, js_responses_len, output_dir, hash_set, min_size, uninteresting_patterns, domain, verbose, skipped_counters):
    """
    Processes and saves eligible inline scripts from the page.
    Handles deduplication, filtering, and file saving.
    """
    inline_count = 0
    for script in inline_scripts:
        if not is_interesting_inline_script(script, uninteresting_patterns):
            log.debug(f"⚠️ Skipping uninteresting inline script")
            skipped_counters['uninteresting'] += 1
            continue
        content = script.encode('utf-8')
        if len(content) < min_size:
            log.debug(f"⚠️ Skipping small inline script")
            skipped_counters['small'] += 1
            continue
        content_hash = hashlib.sha256(content).hexdigest()
        if content_hash in hash_set:
            log.debug(f"⚠️ Skipping duplicate inline script")
            skipped_counters['duplicate'] += 1
            continue
        hash_set.add(content_hash)
        filename = f"{domain}_inline_{content_hash[:8]}.js"
        filepath = output_dir / filename
        with open(filepath, 'wb') as f:
            f.write(content)
        inline_count += 1
        if verbose:
            log.debug(f"💾 Saved inline script: {filename}")
    return inline_count

async def download_js_files(target_url: str, output_root: str, filter_mode: str = "strict",
                           timeout: int = 60000, rate_limit: float = 1, verbose: bool = False,
                           min_size: int = 150, crawl: bool = False, max_depth: int = 1,
                           include_cross_origin: bool = False, clear_output: bool = False):
    """
    Main function to download JavaScript files (external and inline) from a target URL.
    Handles filtering, deduplication, crawling, and output management.
    """
    start_time = datetime.now()
    domain = get_domain_from_url(target_url)
    output_dir = Path(output_root) / domain / filter_mode
    if clear_output and output_dir.exists():
        shutil.rmtree(output_dir)
        log.info(f"🗑 Cleared output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    log.info(f"📂 Saving JS files to: {output_dir}/")

    # Set up verbose logging if requested
    if verbose:
        # Add file handler for verbose logging
        handler = logging.FileHandler(str(output_dir / 'verbose.log'))
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        log.addHandler(handler)
    try:
        # Select filtering patterns based on mode
        uninteresting_patterns = UNINTERESTING_JS_STRICT if filter_mode == "strict" else UNINTERESTING_JS_RELAXED
        log_info_block(f"""
🚀 JS File Downloader Started
Target URL:         {target_url}
Output Directory:   {output_root}
Timeout:            {timeout/1000:.1f}s
Delay:              {rate_limit}s
Filter Mode:        {filter_mode}
Min File Size:      {min_size} bytes
Crawl:              {'Enabled' if crawl else 'Disabled'}
Max Depth:          {max_depth}
Cross-Origin:       {'Enabled' if include_cross_origin else 'Disabled'}
Clear Output Dir:   {'Enabled' if clear_output else 'Disabled'}
        """)
        log.info(f"🔒 Using {'STRICT' if filter_mode == 'strict' else 'RELAXED'} filtering mode")

        domain = get_domain_from_url(target_url)
        output_dir = Path(output_root) / domain / filter_mode
        if clear_output and output_dir.exists():
            shutil.rmtree(output_dir)
            log.info(f"🗑 Cleared output directory: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        log.info(f"📂 Saving JS files to: {output_dir}/")

        hash_set = set()
        errors = []
        skipped_counters = {'small': 0, 'duplicate': 0, 'uninteresting': 0}

        playwright = browser = context = page = None
        try:
            # Launch browser and set up event handlers
            playwright, browser, context, page = await setup_browser()
            collect_js_urls(page, output_dir, hash_set, uninteresting_patterns, include_cross_origin, min_size, verbose, skipped_counters, domain)
            log.info(f"🌐 Navigating to {target_url}...")

            scaled_timeout = int(timeout)
            try:
                # Navigate to the target URL and wait for network to settle
                await page.goto(target_url, wait_until="networkidle", timeout=scaled_timeout)
                await page.wait_for_timeout(10000)  # Wait for network to settle
            except Exception as e:
                # Handle navigation errors gracefully
                log.warning(f"⚠️ Navigation issue: {e}. Continuing with collected responses.")
                errors.append(f"Initial navigation error: {e}")

            # Scroll to trigger lazy loading of scripts
            await page.mouse.wheel(0, 2000)
            await page.wait_for_timeout(2000)

            def normalize_url(url):
                """
                Normalizes a URL for consistent comparison (removes www, lowercases, strips trailing slash).
                Used for deduplication during crawling.
                """
                parsed = urlparse(url)
                netloc = parsed.netloc.lower()
                if netloc.startswith('www.'):
                    netloc = netloc[4:]
                path = parsed.path.rstrip('/')
                normalized = urlunparse((parsed.scheme.lower(), netloc, path, '', '', ''))
                return normalized

            async def crawl_links(context, current_url, max_depth=1, visited=None):
                """
                Recursively crawls internal links up to max_depth, collecting JS files from each page.
                Avoids revisiting the same URLs.
                """
                if not crawl:
                    return
                if visited is None:
                    visited = set()

                normalized_url = normalize_url(current_url)
                if normalized_url in visited:
                    return
                visited.add(normalized_url)

                if max_depth <= 0:
                    return

                page = await context.new_page()
                collect_js_urls(page, output_dir, hash_set, uninteresting_patterns, include_cross_origin, min_size, verbose, skipped_counters, domain)
                try:
                    log.info(f"🔗 Crawling: {current_url}")
                    await page.goto(current_url, wait_until="networkidle", timeout=scaled_timeout)
                    await page.wait_for_timeout(1000)
                    links = await page.query_selector_all('a[href]')
                    hrefs = []
                    for link in links:
                        try:
                            href = await link.get_attribute('href')
                            if href:
                                href = urljoin(current_url, href)
                                href_norm = normalize_url(href)
                                if get_domain_from_url(href) == domain and href_norm not in visited:
                                    hrefs.append(href)
                        except Exception as e:
                            log.debug(f"⚠️ Failed to get href: {e}")

                    for href in hrefs:
                        await crawl_links(context, href, max_depth - 1, visited)
                except Exception as e:
                    log.warning(f"⚠️ Failed to crawl {current_url}: {e}")
                    errors.append(f"Crawl error: {current_url} - {str(e)}")
                finally:
                    await page.close()

            # Start crawling if enabled
            await crawl_links(context, target_url, max_depth=max_depth)

            # Extract and process inline scripts
            inline_scripts = await extract_inline_scripts(page)
            eligible_inline = [s for s in inline_scripts if len(s.encode('utf-8')) >= min_size and
                               hashlib.sha256(s.encode('utf-8')).hexdigest() not in hash_set and
                               is_interesting_inline_script(s, uninteresting_patterns)]
            log_info_block(f"""
📊 JS Collection Summary
Inline scripts found:    {len(inline_scripts)}
Eligible inline scripts: {len(eligible_inline)}
            """)

            # Only process inline scripts here
            await process_inline_scripts(inline_scripts, 0, output_dir, hash_set, min_size, uninteresting_patterns, domain, verbose, skipped_counters)

            duration = (datetime.now() - start_time).total_seconds()
            log_info_block(f"""
🎉 Download Complete!
Total JS files downloaded: {len([f for f in output_dir.iterdir() if f.is_file() and f.suffix == '.js'])}
Skipped: {skipped_counters['uninteresting']} uninteresting, {skipped_counters['small']} small, {skipped_counters['duplicate']} duplicate scripts
Elapsed time: {duration:.2f} seconds
            """)
            if errors:
                log_info_block(f"⚠️ Total errors: {len(errors)}\n" + "\n".join(errors))
        finally:
            # Ensure browser and Playwright are closed properly
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
    finally:
        # Remove verbose log handler if it was added
        if verbose:
            log.handlers = [h for h in log.handlers if not isinstance(h, logging.FileHandler)]

def log_info_block(msg: str):
    """
    Print a visually separated info block for major steps.
    Uses plain print to avoid logger prefix (INFO:) for block headers.
    """
    border = "═" * 70
    print("\n" + border)
    for line in msg.strip().splitlines():
        print(f"║ {line.strip()}")
    print(border + "\n")

if __name__ == "__main__":
    # Argument parsing for CLI usage
    parser = argparse.ArgumentParser(
        description="Download and archive JavaScript files (external and inline) from a target URL using Playwright. Supports filtering, crawling, deduplication, and advanced output options."
    )
    # --------------------------
    # CLI Arguments
    # --------------------------
    parser.add_argument(
        "url",
        nargs="?",
        help="Target URL to analyze (e.g., https://example.com)"
    )
    parser.add_argument(
        "--url-file",
        help="Path to a text file containing one URL per line (optional, overrides positional URL)"
    )
    parser.add_argument(
        "-o", "--output",
        default="getJsOutput",
        help="Directory to save downloaded JavaScript files (default: ./getJsOutput)"
    )
    parser.add_argument(
        "-t", "--timeout",
        type=float,
        default=60.0,
        help="Navigation timeout per page (seconds, default: 60)"
    )
    parser.add_argument(
        "-r", "--delay",
        type=float,
        default=0.5,
        help="Delay between requests/downloads (seconds, default: 0.5)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output and save detailed logs to verbose.log"
    )
    parser.add_argument(
        "--filter",
        choices=["strict", "relaxed"],
        default="strict",
        help="Filtering mode for uninteresting JS files: 'strict' (default) or 'relaxed'"
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=150,
        help="Minimum file size in bytes to save (default: 150)"
    )
    parser.add_argument(
        "--crawl",
        action="store_true",
        default=False,
        help="Enable crawling of internal links on the page (default: disabled)"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=2,
        help="Maximum crawl depth for following links (default: 2)"
    )
    parser.add_argument(
        "--cross-origin",
        action="store_true",
        help="Include cross-origin JavaScript files (default: only same-origin)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear output directory before saving new files"
    )
    args = parser.parse_args()

    # Determine URLs to process (from file or CLI argument)
    urls = []
    if args.url_file:
        # Read URLs from file, skipping comments and blank lines
        url_file_path = Path(args.url_file)
        if not url_file_path.exists():
            log.error(f"❌ URL file not found: {args.url_file}")
            exit(1)
        with open(url_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                urls.append(line)
        if not urls:
            log.error("❌ No valid URLs found in the file.")
            exit(1)
    elif args.url:
        urls = [args.url]
    else:
        log.error("❌ You must provide a URL or --url-file.")
        exit(1)

    # Process each URL
    for url in urls:
        if not validators.url(url):
            log.error(f"❌ Invalid URL: {url}")
            continue
        
        try:
            log.info(f"Processing URL: {url}")
            asyncio.run(
                download_js_files(
                    url,
                    args.output,
                    args.filter,
                    args.timeout * 1000,
                    args.delay,
                    args.verbose,
                    args.min_size,
                    args.crawl,
                    args.max_depth,
                    args.cross_origin,
                    args.clear
                )
            )
        except asyncio.TimeoutError:
            log.error(f"❌ Timeout error: The website at {url} took too long to respond. Try increasing timeout with -t option.")
        except ConnectionRefusedError:
            log.error(f"❌ Connection refused: The server at {url} actively refused the connection.")
        except Exception as e:
            # Handle common HTTP and connection errors with user-friendly messages
            if "403" in str(e):
                log.error(f"❌ Access forbidden (HTTP 403): The server at {url} denied access. The site may have protection against scraping.")
            elif "404" in str(e):
                log.error(f"❌ Page not found (HTTP 404): The requested URL {url} was not found on the server.")
            elif "401" in str(e):
                log.error(f"❌ Authentication required (HTTP 401): The server at {url} requires authentication.")
            elif "SSL" in str(e) or "certificate" in str(e).lower():
                log.error(f"❌ SSL/TLS error: Could not establish a secure connection to {url}. Certificate may be invalid.")
            elif "DNS" in str(e):
                log.error(f"❌ DNS resolution error: Could not resolve host name in {url}. Check the URL.")
            else:
                log.error(f"❌ Error processing {url}: {str(e)}")
            
            # Print more helpful troubleshooting info if verbose
            if args.verbose:
                import traceback
                log.debug("Detailed error information:")
                log.debug(traceback.format_exc())
                log.debug("Try using --verbose for more detailed logs")
                import traceback
                log.debug("Detailed error information:")
                log.debug(traceback.format_exc())
                log.debug("Try using --verbose for more detailed logs")


