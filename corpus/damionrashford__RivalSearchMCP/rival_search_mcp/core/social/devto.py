"""
Dev.to search implementation using the public Forem API.

Dev.to / Forem has no anonymous full-text search endpoint. We approximate
it by combining two signals:

1. Tag lookup via GET /api/articles?tag=<slug> -- fast and precise when the
   query matches (or closely matches) an actual Dev.to tag.
2. Recent-articles fallback via GET /api/articles?per_page=100 -- widely
   sorted listing filtered client-side when tag lookup returns nothing.

Results from both are merged and deduped by URL.
"""

import re
from typing import Any, Dict, List, Optional

import httpx

from rival_search_mcp.logging.logger import logger

_TAG_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _candidate_slugs(query: str) -> List[str]:
    """Dev.to tags are lowercase alphanumeric. Produce plausible slug
    variants so we hit known tags like `python`, `webdev`, `machinelearning`,
    or `rust` for inputs like "Python", "Web Dev", "machine learning"."""
    q = (query or "").strip().lower()
    if not q:
        return []
    candidates: List[str] = []
    flat = _TAG_SLUG_RE.sub("", q)
    if flat:
        candidates.append(flat)
    tokens = [t for t in _TAG_SLUG_RE.split(q) if t]
    if len(tokens) > 1 and tokens[0] not in candidates:
        candidates.append(tokens[0])
    if len(tokens) > 1 and tokens[-1] not in candidates:
        candidates.append(tokens[-1])
    return candidates


def _format(article: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": article.get("title", ""),
        "description": article.get("description", ""),
        "url": article.get("url", ""),
        "published_at": article.get("published_at", ""),
        "tag_list": article.get("tag_list", []),
        "reading_time_minutes": article.get("reading_time_minutes", 0),
        "public_reactions_count": article.get("public_reactions_count", 0),
        "comments_count": article.get("comments_count", 0),
        "user": article.get("user", {}).get("name", ""),
        "source": "devto",
    }


def _matches(article: Dict[str, Any], query: str) -> bool:
    """Case-insensitive substring match across title, description, and tags."""
    if not query:
        return True
    q = query.lower()
    haystack = " ".join(
        [
            article.get("title", ""),
            article.get("description", ""),
            " ".join(article.get("tag_list", [])),
        ]
    ).lower()
    return q in haystack


class DevToSearch:
    """Search Dev.to articles using the public Forem API."""

    def __init__(self):
        self.api_url = "https://dev.to/api"
        self.headers = {
            "User-Agent": (
                "rivalsearchmcp/1.0 (+https://github.com/damionrashford/RivalSearchMCP)"
            ),
            "Accept": "application/json",
        }

    async def search(
        self,
        query: str,
        tag: Optional[str] = None,
        per_page: int = 10,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        seen_urls: set = set()

        async with httpx.AsyncClient(
            headers=self.headers, timeout=30.0, follow_redirects=True
        ) as client:
            # Phase 1: tag lookup(s)
            tags_to_try: List[str] = []
            if tag:
                tags_to_try.append(tag.strip().lower())
            tags_to_try.extend(_candidate_slugs(query))
            for slug in list(dict.fromkeys(tags_to_try)):  # dedupe, preserve order
                if len(results) >= per_page:
                    break
                try:
                    r = await client.get(
                        f"{self.api_url}/articles",
                        params={"tag": slug, "per_page": min(30, per_page * 2)},
                    )
                    if r.status_code != 200:
                        logger.debug("Dev.to tag=%s returned %s", slug, r.status_code)
                        continue
                    for article in r.json():
                        if len(results) >= per_page:
                            break
                        if not _matches(article, query):
                            continue
                        url = article.get("url", "")
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)
                        results.append(_format(article))
                except httpx.HTTPError as e:
                    logger.warning("Dev.to tag=%s failed: %s", slug, e)

            # Phase 2: fallback to recent articles, filter client-side
            if len(results) < per_page:
                try:
                    r = await client.get(f"{self.api_url}/articles", params={"per_page": 100})
                    if r.status_code == 200:
                        for article in r.json():
                            if len(results) >= per_page:
                                break
                            if not _matches(article, query):
                                continue
                            url = article.get("url", "")
                            if url in seen_urls:
                                continue
                            seen_urls.add(url)
                            results.append(_format(article))
                    else:
                        logger.warning(
                            "Dev.to recent-articles fallback returned %s (body: %s)",
                            r.status_code,
                            r.text[:200],
                        )
                except httpx.HTTPError as e:
                    logger.warning("Dev.to recent-articles fallback failed: %s", e)

        logger.info("Found %d Dev.to articles for %r", len(results), query)
        return results[:per_page]
