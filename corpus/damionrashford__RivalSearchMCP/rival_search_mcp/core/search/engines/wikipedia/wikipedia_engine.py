"""
Wikipedia search engine implementation using public API.
No authentication required.
"""

from datetime import datetime
from typing import List

from scrapling.fetchers import AsyncFetcher

from rival_search_mcp.logging.logger import logger

from ...core.multi_engines import BaseSearchEngine, MultiSearchResult


class WikipediaSearchEngine(BaseSearchEngine):
    """Wikipedia search using public MediaWiki API."""

    def __init__(self):
        super().__init__("Wikipedia", "https://en.wikipedia.org")
        self.api_url = "https://en.wikipedia.org/w/api.php"

    async def search(
        self,
        query: str,
        num_results: int = 10,
        extract_content: bool = True,
        follow_links: bool = True,
        max_depth: int = 2,
    ) -> List[MultiSearchResult]:
        """Search Wikipedia articles."""
        try:
            logger.info(f"Starting Wikipedia search for: {query}")

            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "srlimit": num_results,
                "format": "json",
                "utf8": 1,
            }

            response = await AsyncFetcher.get(
                self.api_url,
                params=params,
                stealthy_headers=False,
                headers={"Accept": "application/json"},
            )
            if response.status != 200:
                logger.warning("Wikipedia API returned %s", response.status)
                return []

            data = response.json()
            results = []

            for i, item in enumerate(data.get("query", {}).get("search", [])[:num_results]):
                title = item.get("title", "")
                page_id = item.get("pageid", "")
                snippet = (
                    item.get("snippet", "")
                    .replace('<span class="searchmatch">', "")
                    .replace("</span>", "")
                )

                url = f"{self.base_url}/wiki/{title.replace(' ', '_')}"

                description = snippet
                if extract_content and page_id:
                    extract = await self._get_article_extract(page_id)
                    if extract:
                        description = extract

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

            logger.info(f"Wikipedia search completed: {len(results)} articles")
            return results

        except Exception as e:
            logger.error(f"Wikipedia search failed: {e}")
            return []

    async def _get_article_extract(self, page_id: str) -> str:
        """Get article extract (summary) from Wikipedia."""
        try:
            params = {
                "action": "query",
                "prop": "extracts",
                "exintro": True,
                "explaintext": True,
                "pageids": page_id,
                "format": "json",
            }

            response = await AsyncFetcher.get(
                self.api_url,
                params=params,
                stealthy_headers=False,
                headers={"Accept": "application/json"},
            )
            if response.status != 200:
                return ""

            data = response.json()
            pages = data.get("query", {}).get("pages", {})

            if pages:
                page_data = list(pages.values())[0]
                extract = page_data.get("extract", "")
                return extract[:500] + ("..." if len(extract) > 500 else "")

            return ""

        except Exception as e:
            logger.debug(f"Failed to get Wikipedia extract: {e}")
            return ""
