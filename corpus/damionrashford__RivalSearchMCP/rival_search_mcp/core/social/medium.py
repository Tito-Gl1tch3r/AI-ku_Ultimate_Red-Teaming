"""
Medium search implementation using public RSS feeds.

Medium has no anonymous search API. We approximate search by:

1. Fetching Medium's tag RSS feed (`/feed/tag/<slug>`). Slugs are derived
   from the query with plausible variants so "Artificial Intelligence"
   hits `/feed/tag/artificial-intelligence`.
2. If the tag feed is empty or 404s, falling back to Medium's topic
   feed (`/feed/topic/<slug>`) and then to an HTML scrape of
   `/search?q=<query>` as a last resort.

RSS `summary` fields contain raw HTML (images, linked byline, etc.) --
we strip it with Scrapling so consumers get clean text excerpts
rather than unreadable markup blobs.
"""

import re
from typing import Any, Dict, List, Optional

import feedparser
import httpx
from scrapling.parser import Selector

from rival_search_mcp.logging.logger import logger

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _candidate_slugs(query: str) -> List[str]:
    """Medium tag slugs are lowercase hyphenated (artificial-intelligence,
    machine-learning) or solid (ai, ml). Produce both forms."""
    q = (query or "").strip().lower()
    if not q:
        return []
    slugs: List[str] = []
    hyphen = _SLUG_RE.sub("-", q).strip("-")
    if hyphen:
        slugs.append(hyphen)
    solid = _SLUG_RE.sub("", q)
    if solid and solid != hyphen:
        slugs.append(solid)
    tokens = [t for t in _SLUG_RE.split(q) if t]
    if len(tokens) > 1 and tokens[0] not in slugs:
        slugs.append(tokens[0])
    return slugs


def _clean_excerpt(html: str, max_chars: int = 280) -> str:
    """Strip HTML from an RSS summary to a plain-text excerpt."""
    if not html:
        return ""
    text = Selector(content=html).get_all_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return text


def _format_entry(entry: Any) -> Dict[str, Any]:
    return {
        "title": entry.get("title", ""),
        "url": entry.get("link", ""),
        "author": entry.get("author", "") or entry.get("dc_creator", ""),
        "published": entry.get("published", ""),
        "summary": _clean_excerpt(entry.get("summary", "")),
        "source": "medium",
    }


class MediumSearch:
    """Search Medium articles via public RSS feeds."""

    def __init__(self):
        self.base_url = "https://medium.com"
        self.headers = {
            "User-Agent": (
                "rivalsearchmcp/1.0 (+https://github.com/damionrashford/RivalSearchMCP)"
            ),
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        }

    async def search(
        self,
        query: str,
        tag: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        seen_urls: set = set()

        slugs: List[str] = []
        if tag:
            slugs.append(tag.strip().lower().replace(" ", "-"))
        slugs.extend(_candidate_slugs(query))
        slugs = list(dict.fromkeys(slugs))  # dedupe, preserve order

        async with httpx.AsyncClient(
            headers=self.headers, timeout=30.0, follow_redirects=True
        ) as client:
            # Phase 1: tag feeds
            for slug in slugs:
                if len(results) >= limit:
                    break
                feed_url = f"{self.base_url}/feed/tag/{slug}"
                try:
                    r = await client.get(feed_url)
                    if r.status_code != 200:
                        logger.debug("Medium /feed/tag/%s returned %s", slug, r.status_code)
                        continue
                    feed = feedparser.parse(r.text)
                    for entry in feed.entries:
                        if len(results) >= limit:
                            break
                        url = entry.get("link", "")
                        if not url or url in seen_urls:
                            continue
                        seen_urls.add(url)
                        results.append(_format_entry(entry))
                except httpx.HTTPError as e:
                    logger.warning("Medium /feed/tag/%s failed: %s", slug, e)

            # Phase 2: topic feeds (broader than tags for general queries)
            if len(results) < limit:
                for slug in slugs:
                    if len(results) >= limit:
                        break
                    topic_url = f"{self.base_url}/feed/topic/{slug}"
                    try:
                        r = await client.get(topic_url)
                        if r.status_code != 200:
                            continue
                        feed = feedparser.parse(r.text)
                        for entry in feed.entries:
                            if len(results) >= limit:
                                break
                            url = entry.get("link", "")
                            if not url or url in seen_urls:
                                continue
                            seen_urls.add(url)
                            results.append(_format_entry(entry))
                    except httpx.HTTPError as e:
                        logger.debug("Medium /feed/topic/%s failed: %s", slug, e)
                        continue

            # Phase 3: HTML search scrape
            if not results:
                try:
                    r = await client.get(
                        f"{self.base_url}/search",
                        params={"q": query},
                    )
                    if r.status_code == 200:
                        sel = Selector(content=r.text)
                        for a_el in sel.css("a"):
                            if len(results) >= limit:
                                break
                            href = a_el.attrib.get("href", "")
                            if not href or ("/p/" not in href and "/@" not in href):
                                continue
                            title = a_el.get_all_text(strip=True)
                            if not title or len(title) < 10:
                                continue
                            url = href if href.startswith("http") else f"{self.base_url}{href}"
                            if url in seen_urls:
                                continue
                            seen_urls.add(url)
                            results.append(
                                {
                                    "title": title,
                                    "url": url,
                                    "author": "",
                                    "published": "",
                                    "summary": "",
                                    "source": "medium",
                                }
                            )
                    else:
                        logger.warning("Medium /search returned %s for %r", r.status_code, query)
                except httpx.HTTPError as e:
                    logger.warning("Medium /search fallback failed: %s", e)

        logger.info("Found %d Medium articles for %r", len(results), query)
        return results[:limit]
