import json
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Set, Dict
from dataclasses import dataclass
import time
import datetime


@dataclass
class UrlItem:
    """Represents a found url item."""
    url: str = ""

@dataclass
class Results:
    internal: List[UrlItem]
    external: List[UrlItem]
    

class Crawler:
    """A web crawler that extracts urls from websites."""
    
    def __init__(self, url: str, max_pages: int = 50, timeout: int = 30, delay: float = 1.0, verbose: bool = False, recursive: bool = False, verify_ssl: bool = True, same_domain_only: bool = True, depth: int = 3, _on_result_callback = None):
        """
        Initialize the crawler.
        
        Args:
            url: The URL to crawl
            max_pages: Maximum number of pages to crawl
            timeout: Request timeout in seconds
            delay: Delay between requests in seconds
            verbose: Print every page being searched
            recursive: Follow every internal link (default: only crawl the final page after redirects)
            verify_ssl: Whether to verify SSL certificates (default: True)
            same_domain_only: Whether to only extract URLs from the same domain (default: True)
            depth: The depth to go for recursiveness. Doesn't work if same_domain_only is set to True. 
        """
        self.url = url
        self.max_pages = max_pages
        self.timeout = timeout
        self.delay = delay
        self.verbose = verbose
        self.recursive = recursive
        self.depth = 1 if same_domain_only else depth
        self.verify_ssl = verify_ssl
        self.final_url = url
        self.same_domain_only = same_domain_only
        self.visited_urls: Set[str] = set()  # Stores normalized URLs to prevent duplicate visits
        self.results = Results(internal=[], external=[])
        self._seen_values: Set[str] = set()  # Track seen values to prevent duplicates
        self._on_result_callback = _on_result_callback if _on_result_callback else self._default_callback # The callback when a result is found
        
    def _default_callback(self, url, external: bool = False):
        if not self.verbose:
            return
        scope = "EXTERNAL" if external else "INTERNAL"
        print(f"[{scope}]: {url}")
        
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication by removing fragments, query params, and trailing slashes."""
        try:
            parsed = urlparse(url)
            # Remove fragment and query parameters
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            # Remove trailing slash except for root path
            if normalized.endswith('/') and len(normalized) > len(f"{parsed.scheme}://{parsed.netloc}"):
                normalized = normalized.rstrip('/')
            return normalized.lower()
        except Exception:
            return url.lower()

    def _is_duplicate(self, value: str) -> bool:
        return value in self._seen_values
    
    def _add_result(self, value: str, source_url: str):
        """Add a result if it's not a duplicate."""
        if self._is_duplicate(value):
            return
        self._seen_values.add(value)
        if self._is_same_domain(value,source_url):
            self.results.internal.append(UrlItem(
                url=value,
            ))
            if self._on_result_callback:
                self._on_result_callback(value, False)
        elif not self.same_domain_only:
            if self._on_result_callback:
                self._on_result_callback(value, True)
            self.results.external.append(UrlItem(
                url=value,
            ))
    
    def _ensure_protocol(self, url: str) -> str:
        """Ensure URL has a protocol."""
        if not url.startswith(('http://', 'https://')):
            return 'https://' + url
        return url
    
    def _get_final_url(self, url: str) -> str:
        """Follow redirects to get the final URL."""
        try:
            response = requests.head(url, verify=self.verify_ssl, timeout=self.timeout, allow_redirects=True)
            return response.url
        except Exception:
            return url
    
    def _is_same_domain(self, url: str, base_url: str) -> bool:
        """Check if URL belongs to the same domain."""
        try:
            parsed_url = urlparse(url)
            parsed_base = urlparse(base_url)
            return parsed_url.netloc == parsed_base.netloc
        except Exception:
            return False
    
    def _extract_urls(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
        """Extract urls from the page."""
        links = set()
        
        try:
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if not href:
                    continue
                    
                # Resolve relative URLs
                absolute_url = urljoin(base_url, href)
                
                # Normalize URL for deduplication
                normalized_url = self._normalize_url(absolute_url)
                
                # Check if it's an internal link and not already visited (using normalized URL)
                if normalized_url not in self.visited_urls:
                    # Filter out common non-content URLs
                    if not any(exclude in absolute_url.lower() for exclude in [
                        '#', 'javascript:', 'mailto:', 'tel:', '.pdf', '.doc', '.docx', 
                        '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.xml', '.rss',
                        'logout', 'admin', 'login', 'register', 'signup', 'signin'
                    ]):
                        links.add(absolute_url)
                        
        except Exception:
            pass
            
        return links

    def _extract_urls_from_text(self, text: str) -> List[str]:
        """Extract URLs from text using regex."""
        # More comprehensive URL pattern that matches various URL formats
        url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.-]*(?:\?(?:[\w&=%.-])*)?(?:#(?:[\w.-])*)?)?)?'
        urls = re.findall(url_pattern, text, re.IGNORECASE)
        
        # Debug: print what we found
        if hasattr(self, 'verbose') and self.verbose:
            print(f"  Found {len(urls)} raw URLs in text")
            if urls:
                print(f"  First few URLs: {urls[:3]}")
        
        # Clean up and validate URLs
        clean_urls = []
        for url in urls:
            # Remove trailing punctuation that might have been captured
            url = url.rstrip('.,;!?')
            if url and len(url) > 10:  # Basic validation
                clean_urls.append(url)
        
        if hasattr(self, 'verbose') and self.verbose:
            print(f"  After cleaning: {len(clean_urls)} URLs")
        
        return clean_urls

    def _process_page(self, url: str) -> Dict[str, List[str]]:
        """Process a single page and extract urls."""
        try:
            # Add delay to be respectful to the server
            if len(self.visited_urls) > 0:
                time.sleep(self.delay)
            
            if self.verbose:
                print(f"Searching: {url}")
            
            # Get the page
            response = requests.get(url, verify=self.verify_ssl, timeout=self.timeout)
            
            # Only proceed if we get a 200 status code
            if response.status_code != 200:
                if self.verbose:
                    print(f"Skipping {url}: HTTP {response.status_code}")
                return {"urls": []}
            
            # Parse HTML content
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            visible_text = soup.get_text(separator=' ')
            
            # Extract URLs from visible text
            text_urls = self._extract_urls_from_text(visible_text)
            
            # Extract URLs from HTML links
            link_urls = []
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href:
                    # Convert relative URLs to absolute
                    if href.startswith(('http://', 'https://')):
                        link_urls.append(href)
                    elif href.startswith('/'):
                        # Relative URL
                        parsed_base = urlparse(url)
                        absolute_url = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
                        link_urls.append(absolute_url)
            
            if self.verbose:
                print(f"  Found {len(link_urls)} URLs from HTML links")
            
            # Combine all URLs and remove duplicates
            all_urls = list(set(text_urls + link_urls))
            
            # Filter based on same_domain_only setting
            if self.same_domain_only:
                filtered_urls = []
                for found_url in all_urls:
                    if self._is_same_domain(found_url, url):
                        filtered_urls.append(found_url)
                all_urls = filtered_urls
                
                if self.verbose:
                    print(f"After same_domain_only filtering: {len(all_urls)} URLs")
            # If same_domain_only=False, keep all URLs (no filtering needed)
            
            if self.verbose:
                print(f"Total unique URLs found: {len(all_urls)}")
                if all_urls:
                    print(f"Sample URLs: {all_urls[:3]}")
                    
            return {
                "urls": all_urls,
            }
            
        except Exception as e:
            if self.verbose:
                print(f"Error processing {url}: {str(e)}")
            return {"urls": []}
    
    def fetch(self):
        """Fetch the initial URL and follow redirects."""
        try:
            # Ensure URL has protocol
            self.url = self._ensure_protocol(self.url)
            
            # Get final URL after redirects
            self.final_url = self._get_final_url(self.url)
            
        except Exception as e:
            raise RuntimeError(f"Failed to fetch URL: {str(e)}")
    
    def extract_urls(self):
        """Extract urls from the website."""
        self._crawl_and_extract()

    
    def _crawl_and_extract(self):
        """Crawl the website and extract urls."""
        if not self.final_url:
            raise RuntimeError("Must call fetch() before extracting data")
        
        if self.recursive:
            # Recursive mode: crawl multiple pages
            urls_to_visit = {self.final_url}
            page_count = 0
            
            while urls_to_visit and page_count < self.max_pages:
                current_url = urls_to_visit.pop()
                
                # Normalize URL for deduplication
                normalized_url = self._normalize_url(current_url)
                
                if normalized_url in self.visited_urls:
                    continue
                    
                self.visited_urls.add(normalized_url)
                page_count += 1
                
                # Process the page
                page_data = self._process_page(current_url)
                
                # Add urls to results
                for url in page_data["urls"]:
                    self._add_result(url, current_url)
                
                # Extract internal links for further crawling
                if page_count < self.max_pages:
                    try:
                        response = requests.get(current_url, verify=self.verify_ssl, timeout=self.timeout)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            new_links = self._extract_urls(soup, current_url)
                            urls_to_visit.update(new_links)
                    except Exception:
                        continue
        else:
            # Non-recursive mode: only crawl the final page
            normalized_url = self._normalize_url(self.final_url)
            self.visited_urls.add(normalized_url)
            page_data = self._process_page(self.final_url)
            
            # Add urls to results
            for url in page_data["urls"]:
                self._add_result(url, self.final_url)
    
    def get_results(self) -> List[UrlItem]:
        """Get the extracted results (already deduplicated)."""
        return self.results
    
    def save_to_file(self, file: str = None) -> None:
        timestamp = datetime.datetime.now().isoformat()
        filename = file if file else f"{self.url}-{timestamp}"
        with open(filename, "w") as file:
            results = {
                "base_url": self.url, 
                "final_url": self.final_url,
                "timestamp": timestamp,
                "internal_links": [item.url for item in self.results.internal],
                "external_links": [item.url for item in self.results.external],
            }
            json.dump(results, file)