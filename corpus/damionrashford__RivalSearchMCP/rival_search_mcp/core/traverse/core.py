#!/usr/bin/env python3
"""
Core website traversal functionality for RivalSearchMCP.
Main WebsiteTraverser class for crawling and exploring websites.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx
from scrapling.parser import Selector

from rival_search_mcp.logging.logger import logger
from rival_search_mcp.utils import clean_html_to_markdown, clean_text

# Configuration
MAX_DEPTH = 3
MAX_PAGES = 50
DELAY_BETWEEN_REQUESTS = 0.5
MAX_CONCURRENT_REQUESTS = 5


class WebsiteTraverser:
    """Website traversal and crawling engine."""

    def __init__(self):
        """Initialize the traverser."""
        self.visited_urls: Set[str] = set()
        self.pages: List[Dict[str, Any]] = []
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def traverse_website(
        self,
        start_url: str,
        max_depth: int = MAX_DEPTH,
        max_pages: int = MAX_PAGES,
        delay: float = DELAY_BETWEEN_REQUESTS,
    ) -> List[Dict[str, Any]]:
        """
        Traverse a website starting from the given URL.

        Args:
            start_url: Starting URL for traversal
            max_depth: Maximum depth to traverse
            max_pages: Maximum number of pages to visit
            delay: Delay between requests

        Returns:
            List of page data dictionaries
        """
        logger.info(f"🌐 Starting website traversal from: {start_url}")
        logger.info(f"📊 Max depth: {max_depth}, Max pages: {max_pages}")

        self.visited_urls.clear()
        self.pages.clear()

        await self._traverse_recursive(start_url, 0, max_depth, max_pages, delay)

        logger.info(f"✅ Traversal completed. Visited {len(self.pages)} pages")
        return self.pages

    async def _traverse_recursive(
        self, url: str, depth: int, max_depth: int, max_pages: int, delay: float
    ):
        """Recursively traverse the website."""
        if depth > max_depth or len(self.pages) >= max_pages or url in self.visited_urls:
            return

        self.visited_urls.add(url)

        try:
            async with self.semaphore:
                page_data = await self._fetch_page(url)
                if page_data:
                    self.pages.append(page_data)
                    logger.info(f"📄 Fetched: {url} (depth {depth})")

                    # Find links for next level
                    if depth < max_depth and len(self.pages) < max_pages:
                        links = self._extract_links(page_data["html"], url)
                        await asyncio.sleep(delay)

                        # Process links concurrently
                        tasks = []
                        for link in links[:10]:  # Limit concurrent tasks
                            if link not in self.visited_urls:
                                task = self._traverse_recursive(
                                    link, depth + 1, max_depth, max_pages, delay
                                )
                                tasks.append(task)

                        if tasks:
                            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"Error traversing {url}: {e}")

    async def _fetch_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch a single page."""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

                return {
                    "url": url,
                    "title": self._extract_title(response.text),
                    "content": self._extract_content(response.text),
                    "html": response.text,
                    "status_code": response.status_code,
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
            return None

    def _extract_title(self, html: str) -> str:
        """Extract page title from HTML."""
        try:
            el = Selector(content=html).css_first("title")
            return clean_text(el.get_all_text(strip=True)) if el else ""
        except Exception:
            return ""

    def _extract_content(self, html: str) -> str:
        """Extract main content from HTML."""
        try:
            return clean_html_to_markdown(html)
        except Exception:
            return ""

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        """Extract links from HTML."""
        try:
            sel = Selector(content=html)
            seen: Set[str] = set()
            unique_links: List[str] = []
            for a_el in sel.css("a[href]"):
                href = a_el.attrib.get("href", "")
                if not href:
                    continue
                absolute_url = urljoin(base_url, href)
                if (
                    absolute_url.startswith("http")
                    and self._is_same_domain(base_url, absolute_url)
                    and absolute_url not in seen
                ):
                    seen.add(absolute_url)
                    unique_links.append(absolute_url)
            return unique_links
        except Exception as e:
            logger.debug(f"Error extracting links: {e}")
            return []

    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs belong to the same domain."""
        try:
            domain1 = urlparse(url1).netloc
            domain2 = urlparse(url2).netloc
            return domain1 == domain2
        except Exception:
            return False
