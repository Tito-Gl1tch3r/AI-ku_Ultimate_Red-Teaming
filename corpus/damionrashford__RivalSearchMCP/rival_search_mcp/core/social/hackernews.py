"""Hacker News search via the Algolia HN Search API."""

from __future__ import annotations

from typing import Any

import httpx

from rival_search_mcp.logging.logger import logger
from rival_search_mcp.utils.query import normalize_search_query

_API_BASE = "https://hn.algolia.com/api/v1"
_HN_BASE = "https://news.ycombinator.com"


class HackerNewsSearch:
    """Search Hacker News via Algolia (no auth needed)."""

    async def search(
        self,
        query: str,
        tags: str = "(story,comment)",
        sort_by: str = "relevance",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Args:
            tags: Algolia tag filter. Comma-separated = AND; parenthesised
                  comma-separated = OR. Default searches stories and comments.
        """
        normalized = normalize_search_query(query, max_terms=4)
        if normalized != query:
            logger.debug("HackerNews query normalized: %r -> %r", query, normalized)

        endpoint = f"{_API_BASE}/search_by_date" if sort_by == "date" else f"{_API_BASE}/search"
        params: dict[str, Any] = {
            "query": normalized,
            "tags": tags,
            "hitsPerPage": limit,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(endpoint, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "HackerNews search returned %s for %r: %s",
                e.response.status_code,
                query,
                e,
            )
            return []
        except httpx.HTTPError as e:
            logger.error("HackerNews search failed for %r: %s", query, e)
            return []
        except ValueError as e:
            logger.warning("HackerNews returned non-JSON for %r: %s", query, e)
            return []

        items = []
        for hit in data.get("hits", []):
            items.append(
                {
                    "title": hit.get("title") or hit.get("story_title", ""),
                    "author": hit.get("author", ""),
                    "points": hit.get("points", 0),
                    "url": hit.get("url", ""),
                    "hn_url": f"{_HN_BASE}/item?id={hit.get('objectID', '')}",
                    "num_comments": hit.get("num_comments", 0),
                    "created_at": hit.get("created_at", ""),
                    "story_text": (hit.get("story_text") or hit.get("comment_text", ""))[:500],
                    "source": "hackernews",
                }
            )

        logger.info("Found %d HackerNews items for %r", len(items), query)
        return items
