"""
Stack Exchange / Stack Overflow search via the public REST API.

Uses api.stackexchange.com/2.3/search/advanced which does real
full-text search, requires no API key for low-throughput usage
(~300 requests per IP per day with `quota_remaining` returned in
every response), and supports the entire Stack Exchange network
(stackoverflow, serverfault, superuser, askubuntu, etc.) via the
`site` parameter.

Results are returned with title, body-stripped excerpt, score,
view/answer counts, accepted flag, tags, author, and URL.
"""

from typing import Any, Dict, List, Optional

import httpx

from rival_search_mcp.logging.logger import logger

_API_BASE = "https://api.stackexchange.com/2.3"


class StackOverflowSearch:
    """Search Stack Exchange sites (defaults to Stack Overflow)."""

    def __init__(self):
        self.api_url = _API_BASE
        self.headers = {
            "User-Agent": (
                "rivalsearchmcp/1.0 (+https://github.com/damionrashford/RivalSearchMCP)"
            ),
            "Accept": "application/json",
            # Stack Exchange gzip-compresses by default; httpx handles it.
        }

    async def search(
        self,
        query: str,
        site: str = "stackoverflow",
        limit: int = 10,
        sort: str = "relevance",
        accepted_only: bool = False,
        tagged: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search Stack Exchange questions.

        Args:
            query: Search query
            site: Stack Exchange site (stackoverflow, serverfault, askubuntu, etc.)
            limit: Max results (pagesize, 1..100)
            sort: relevance | activity | votes | creation
            accepted_only: Return only questions with accepted answers
            tagged: Restrict to a tag (semicolon-separated for multiple)
        """
        params = {
            "q": query,
            "site": site,
            "pagesize": max(1, min(limit, 100)),
            "order": "desc",
            "sort": sort,
            "filter": "!9Z(-wzftf",  # default filter: title, body excerpt, score, etc.
        }
        if accepted_only:
            params["accepted"] = "True"
        if tagged:
            params["tagged"] = tagged

        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                response = await client.get(f"{self.api_url}/search/advanced", params=params)
                if response.status_code != 200:
                    logger.warning(
                        "Stack Exchange returned %s for %r (body: %s)",
                        response.status_code,
                        query,
                        response.text[:200],
                    )
                    return []

                data = response.json()
                items = data.get("items", [])
                results: List[Dict[str, Any]] = []
                for q in items:
                    owner = q.get("owner") or {}
                    results.append(
                        {
                            "title": q.get("title", ""),
                            "url": q.get("link", ""),
                            "score": q.get("score", 0),
                            "answer_count": q.get("answer_count", 0),
                            "view_count": q.get("view_count", 0),
                            "is_answered": q.get("is_answered", False),
                            "accepted_answer_id": q.get("accepted_answer_id"),
                            "tags": q.get("tags", []),
                            "author": owner.get("display_name", ""),
                            "creation_date": q.get("creation_date", 0),
                            "last_activity_date": q.get("last_activity_date", 0),
                            "source": f"stackexchange:{site}",
                        }
                    )

                if data.get("quota_remaining", 300) < 50:
                    logger.warning(
                        "Stack Exchange quota low: %d remaining (resets daily)",
                        data.get("quota_remaining"),
                    )
                logger.info(
                    "Found %d Stack Exchange questions for %r (site=%s)",
                    len(results),
                    query,
                    site,
                )
                return results

        except httpx.HTTPError as e:
            logger.warning("Stack Exchange search failed (network): %s", e)
            return []
        except Exception:
            logger.exception("Stack Exchange search failed (unexpected)")
            return []
