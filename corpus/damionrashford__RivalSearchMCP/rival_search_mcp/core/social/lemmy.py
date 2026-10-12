"""
Lemmy search via the public v3 API.

Lemmy is the federated Reddit-alternative that powers the threadiverse.
Each instance exposes a JSON API at `/api/v3/search`; searches against
one instance (by default `lemmy.world`, the largest) return results
federated from across the network.

No authentication is required for read-only queries.
"""

from typing import Any, Dict, List

import httpx

from rival_search_mcp.logging.logger import logger


class LemmySearch:
    """Search Lemmy posts via the v3 REST API of a given instance."""

    def __init__(self, instance: str = "lemmy.world"):
        self.instance = instance.rstrip("/")
        self.base_url = f"https://{self.instance}"
        self.api_url = f"{self.base_url}/api/v3"
        self.headers = {
            "User-Agent": (
                "rivalsearchmcp/1.0 (+https://github.com/damionrashford/RivalSearchMCP)"
            ),
            "Accept": "application/json",
        }

    async def search(
        self,
        query: str,
        limit: int = 10,
        sort: str = "TopAll",
        listing_type: str = "All",
        community_name: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Search Lemmy posts across federated communities.

        Args:
            query: Search query
            limit: Max results (1..50)
            sort: TopAll | TopYear | TopMonth | Hot | New | Active | Relevance
            listing_type: All | Local | Subscribed
            community_name: Restrict to a specific community (e.g., "rust@programming.dev")
        """
        params: Dict[str, Any] = {
            "q": query,
            "type_": "Posts",
            "sort": sort,
            "listing_type": listing_type,
            "limit": max(1, min(limit, 50)),
        }
        if community_name:
            params["community_name"] = community_name

        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                response = await client.get(f"{self.api_url}/search", params=params)
                if response.status_code != 200:
                    logger.warning(
                        "Lemmy (%s) returned %s for %r (body: %s)",
                        self.instance,
                        response.status_code,
                        query,
                        response.text[:200],
                    )
                    return []

                data = response.json()
                posts = data.get("posts", [])
                results: List[Dict[str, Any]] = []
                for item in posts:
                    post = item.get("post") or {}
                    creator = item.get("creator") or {}
                    community = item.get("community") or {}
                    counts = item.get("counts") or {}
                    results.append(
                        {
                            "title": post.get("name", ""),
                            "url": post.get("url") or post.get("ap_id", ""),
                            "body": (post.get("body") or "")[:500],
                            "community": community.get("name", ""),
                            "community_title": community.get("title", ""),
                            "author": creator.get("name", ""),
                            "author_display": creator.get("display_name", ""),
                            "score": counts.get("score", 0),
                            "upvotes": counts.get("upvotes", 0),
                            "downvotes": counts.get("downvotes", 0),
                            "comments": counts.get("comments", 0),
                            "published": post.get("published", ""),
                            "ap_id": post.get("ap_id", ""),  # federated ActivityPub id
                            "source": f"lemmy:{self.instance}",
                        }
                    )

                logger.info(
                    "Found %d Lemmy posts for %r (instance=%s)",
                    len(results),
                    query,
                    self.instance,
                )
                return results

        except httpx.HTTPError as e:
            logger.warning("Lemmy search failed (network): %s", e)
            return []
        except Exception:
            logger.exception("Lemmy search failed (unexpected)")
            return []
