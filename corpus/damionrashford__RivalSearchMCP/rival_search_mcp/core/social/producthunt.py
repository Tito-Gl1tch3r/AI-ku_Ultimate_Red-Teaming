"""
Product Hunt search via the public RSS feed.

Product Hunt offers no anonymous search API. Their GraphQL endpoint
(`/frontend/graphql`) is fronted by Cloudflare which challenges
non-browser TLS fingerprints, and their search page is a Next.js SPA
that hydrates results client-side (HTML alone is just a skeleton).

The RSS feed at `/feed` is public, cacheable, and returns the latest
~50 launched products with titles and taglines. We fetch it and
filter client-side against the query. This is "latest products that
mention your query" rather than true search, but it's the strongest
signal available without a headless browser or a paid token.

When the query matches nothing, we return the latest products
unfiltered so callers still get a useful discovery feed.
"""

import re
from typing import Any, Dict, List

import feedparser
import httpx

from rival_search_mcp.logging.logger import logger


def _clean(text: str) -> str:
    """Strip HTML and collapse whitespace."""
    if not text:
        return ""
    # Strip HTML tags without pulling in a full parser for RSS tagline text
    clean = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", clean).strip()


def _matches(entry: Dict[str, str], query: str) -> bool:
    """Case-insensitive substring match across title and summary/tagline."""
    if not query:
        return True
    q = query.lower()
    haystack = (entry.get("title", "") + " " + entry.get("tagline", "")).lower()
    return q in haystack


class ProductHuntSearch:
    """Query Product Hunt's public RSS feed."""

    def __init__(self):
        self.base_url = "https://www.producthunt.com"
        self.feed_url = "https://www.producthunt.com/feed"
        self.headers = {
            "User-Agent": (
                "rivalsearchmcp/1.0 (+https://github.com/damionrashford/RivalSearchMCP)"
            ),
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        }

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                response = await client.get(self.feed_url)
                if response.status_code != 200:
                    logger.warning(
                        "Product Hunt /feed returned %s for %r (body snippet: %s)",
                        response.status_code,
                        query,
                        response.text[:200],
                    )
                    return []

                feed = feedparser.parse(response.text)
                entries: List[Dict[str, Any]] = []
                for entry in feed.entries:
                    item = {
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "tagline": _clean(entry.get("summary", "")),
                        "published": entry.get("published", ""),
                        "author": entry.get("author", ""),
                        "source": "producthunt",
                    }
                    entries.append(item)

                # Prefer query matches; fall back to latest when nothing matches
                matched = [e for e in entries if _matches(e, query)]
                results = matched if matched else entries

                if not matched and query:
                    logger.info(
                        "Product Hunt: 0 matches for %r in latest %d — "
                        "returning recent launches as discovery feed",
                        query,
                        len(entries),
                    )
                else:
                    logger.info("Found %d Product Hunt posts for %r", len(matched), query)
                return results[:limit]

        except httpx.HTTPError as e:
            logger.warning("Product Hunt /feed network error: %s", e)
            return []
        except Exception:
            logger.exception("Product Hunt search failed (unexpected)")
            return []
