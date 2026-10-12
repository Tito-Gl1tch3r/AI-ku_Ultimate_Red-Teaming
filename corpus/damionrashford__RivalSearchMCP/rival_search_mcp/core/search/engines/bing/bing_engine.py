"""
Bing web search engine via www.bing.com/search.

Bing's SERP is Cloudflare/Akamai-fronted and TLS-fingerprints callers.
Scrapling's AsyncFetcher with stealthy_headers=True drives tls_client
with a real browser fingerprint, which is sufficient to receive the
full results HTML. No browser binary required.

Result cards are li.b_algo; title text is inside h2 > a; href on the
link is a Bing redirector (bing.com/ck/...) that resolves to the real
target when followed. BaseSearchEngine._extract_real_url handles the
redirect parameter pattern we care about when extract_content=True.
"""

from datetime import datetime
from typing import List

from scrapling.fetchers import AsyncFetcher

from rival_search_mcp.logging.logger import logger
from rival_search_mcp.utils.query import query_keywords

from ...core.multi_engines import BaseSearchEngine, MultiSearchResult


class BingSearchEngine(BaseSearchEngine):
    """Bing web search via www.bing.com/search (Scrapling-powered)."""

    def __init__(self):
        super().__init__("Bing", "https://www.bing.com")
        self.search_url = f"{self.base_url}/search"

    async def search(
        self,
        query: str,
        num_results: int = 10,
        extract_content: bool = True,
        follow_links: bool = True,
        max_depth: int = 2,
    ) -> List[MultiSearchResult]:
        logger.info("Starting Bing search for: %s", query)

        results = await self._search_html(query, num_results)
        logger.info("Bing returned %d results", len(results))

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
        # mkt=en-US + setlang=en pin results to English; without them Bing
        # geolocates from egress IP and frequently returns non-English
        # results from cloud IPs (e.g. Chinese results for US cloud egress).
        try:
            page = await AsyncFetcher.get(
                self.search_url,
                params={
                    "q": query,
                    "mkt": "en-US",
                    "setlang": "en",
                    "count": min(num_results * 2, 30),
                },
                headers={"Accept-Language": "en-US,en;q=0.9"},
                stealthy_headers=True,
                timeout=30,
            )
        except Exception as e:
            logger.error("Bing fetch failed: %s", e)
            return []

        if page.status != 200:
            logger.warning(
                "Bing returned %s for %r (body snippet: %s)",
                page.status,
                query,
                (page.body or b"")[:200],
            )
            return []

        results: List[MultiSearchResult] = []
        cards = page.css("li.b_algo")
        for i, card in enumerate(cards[:num_results]):
            title_links = card.css("h2 a")
            if not title_links:
                continue
            title = self._clean_text(title_links[0].get_all_text() or "")
            url = title_links[0].attrib.get("href", "")
            if not title or not url:
                continue

            snippet_nodes = card.css("p.b_lineclamp2, p.b_lineclamp3, p.b_paractl, div.b_caption p")
            description = (
                self._clean_text(snippet_nodes[0].get_all_text() or "") if snippet_nodes else ""
            )

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

        keywords = query_keywords(query)
        if keywords and results:
            relevant = [
                r
                for r in results
                if any(kw in (r.title + " " + r.description).lower() for kw in keywords)
            ]
            if not relevant:
                logger.warning(
                    "Bing returned %d results with zero keyword overlap for %r — discarding",
                    len(results),
                    query,
                )
            results = relevant

        return results
