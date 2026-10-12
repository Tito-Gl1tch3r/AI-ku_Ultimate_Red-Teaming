"""
Yahoo search engine implementation for RivalSearchMCP.

The search-page request at search.yahoo.com is Cloudflare-fronted and
TLS-fingerprints clients -- plain httpx is routinely downgraded to
anti-bot interstitials with empty result bodies. Scrapling's
AsyncFetcher with stealthy_headers=True drives tls_client with a real
browser fingerprint, so Yahoo serves the normal SERP HTML.

Result cards live inside div.algo-sr; the title is nested inside an
h3 > span (hence .get_all_text() rather than .text). Content fetching
for result URLs stays on the base httpx session.
"""

from datetime import datetime
from typing import List
from urllib.parse import urlencode

from scrapling.fetchers import AsyncFetcher

from rival_search_mcp.logging.logger import logger

from ...core.multi_engines import BaseSearchEngine, MultiSearchResult


class YahooSearchEngine(BaseSearchEngine):
    """Yahoo search via search.yahoo.com (Scrapling-powered)."""

    def __init__(self):
        super().__init__("Yahoo", "https://search.yahoo.com")
        self.search_url = f"{self.base_url}/search"

    async def search(
        self,
        query: str,
        num_results: int = 10,
        extract_content: bool = True,
        follow_links: bool = True,
        max_depth: int = 2,
    ) -> List[MultiSearchResult]:
        """Search Yahoo and optionally extract result-page content."""
        logger.info("Starting Yahoo search for: %s", query)

        results = await self._search_html(query, num_results)
        logger.info("Yahoo returned %d results", len(results))

        if extract_content and results:
            for result in results:
                result.real_url = self._extract_real_url(result.url)
                target_url = result.real_url if result.real_url != result.url else result.url
                if not target_url:
                    continue

                content = await self._fetch_page_content(target_url)
                if not content:
                    continue

                result.full_content = self._extract_main_content(content)
                result.internal_links = self._extract_internal_links(content, target_url)

                if follow_links and result.internal_links and max_depth > 1:
                    result.second_level_content = await self._extract_second_level_content(
                        target_url, result.internal_links
                    )

        return results

    async def _search_html(self, query: str, num_results: int) -> List[MultiSearchResult]:
        """Query search.yahoo.com via Scrapling and parse result cards."""
        params = {
            "p": query,
            "n": min(num_results, 50),
            "ei": "UTF-8",
            "fr": "yfp-t",
        }
        url = f"{self.search_url}?{urlencode(params)}"

        try:
            page = await AsyncFetcher.get(url, stealthy_headers=True, timeout=30)
        except Exception as e:
            logger.error("Yahoo fetch failed: %s", e)
            return []

        if page.status != 200:
            logger.warning(
                "Yahoo returned %s for %r (body snippet: %s)",
                page.status,
                query,
                (page.body or b"")[:200],
            )
            return []

        results: List[MultiSearchResult] = []
        cards = page.css("div.algo-sr")
        for i, card in enumerate(cards[:num_results]):
            # Title is inside h3 > span. Use get_all_text so the nested
            # span content is included (.text would return empty).
            h3_nodes = card.css("h3")
            if not h3_nodes:
                continue
            title = self._clean_text(h3_nodes[0].get_all_text() or "")

            link_nodes = card.css("div.compTitle a.d-ib")
            if not link_nodes:
                continue
            url = link_nodes[0].attrib.get("href", "")
            if not title or not url:
                continue

            desc_nodes = card.css("div.compText, p.s-desc, span.fc-falcon")
            description = self._clean_text(desc_nodes[0].get_all_text() or "") if desc_nodes else ""

            results.append(
                MultiSearchResult(
                    title=title,
                    url=url,
                    description=description,
                    engine=self.name,
                    position=i + 1,
                    timestamp=datetime.now().isoformat(),
                )
            )
        return results
