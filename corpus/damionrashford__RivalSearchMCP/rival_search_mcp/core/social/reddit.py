"""
Reddit search via Pullpush.io.

Reddit's endpoints are Cloudflare-fronted and block datacenter IPs.
Pullpush.io is a community-maintained Reddit archive with a public
REST API that requires no authentication and has no IP restrictions.

API reference: https://api.pullpush.io/docs
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from rival_search_mcp.logging.logger import logger

_TIME_FILTER_SECONDS: dict[str, int] = {
    "day": 86_400,
    "week": 604_800,
    "month": 2_592_000,
    "year": 31_536_000,
}

_POST_BASE = "https://www.reddit.com"
_API_URL = "https://api.pullpush.io/reddit/search/submission"
_HEADERS = {"User-Agent": "RivalSearchMCP/1.0 (+https://github.com/damionrashford/RivalSearchMCP)"}


class RedditSearch:
    """Search Reddit submissions via Pullpush.io."""

    async def search(
        self,
        query: str,
        subreddit: str = "all",
        time_filter: str = "all",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "q": query,
            "size": min(limit, 100),
        }
        if subreddit and subreddit != "all":
            params["subreddit"] = subreddit
        if time_filter in _TIME_FILTER_SECONDS:
            params["after"] = int(time.time()) - _TIME_FILTER_SECONDS[time_filter]

        try:
            async with httpx.AsyncClient(
                headers=_HEADERS, timeout=30.0, follow_redirects=True
            ) as client:
                response = await client.get(_API_URL, params=params)

            if response.status_code != 200:
                logger.warning(
                    "Pullpush returned %s for %r (body: %s)",
                    response.status_code,
                    query,
                    response.text[:200],
                )
                return []

            data = response.json()

        except httpx.HTTPError as e:
            logger.error("Reddit (Pullpush) request failed for %r: %s", query, e)
            return []
        except ValueError as e:
            logger.warning("Reddit (Pullpush) returned non-JSON for %r: %s", query, e)
            return []

        posts = data.get("data", [])
        logger.info("Found %d Reddit posts for %r via Pullpush", len(posts), query)
        return self._parse_posts(posts)

    def _parse_posts(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results = []
        for post in items:
            permalink = post.get("permalink", "")
            results.append(
                {
                    "title": post.get("title", ""),
                    "subreddit": post.get("subreddit", ""),
                    "author": post.get("author", ""),
                    "score": post.get("score", 0),
                    "url": (f"{_POST_BASE}{permalink}" if permalink else post.get("url", "")),
                    "num_comments": post.get("num_comments", 0),
                    "created_utc": post.get("created_utc", 0),
                    "selftext": post.get("selftext", "")[:500],
                    "source": "reddit",
                }
            )
        return results
