"""
Harvard Dataverse dataset search provider.

Harvard Dataverse (dataverse.harvard.edu) is the largest general-purpose
research-data repository in the world; it's also the reference
implementation of the Dataverse Project, so the same API surface works
against most institutional Dataverse instances if someone wants to
retarget it.

We query `/api/search?type=dataset` which returns metadata-rich dataset
entries: title, authors, DOI, description, publisher, publication date.
No authentication required.
"""

from typing import Any, Dict, List, Optional

import httpx

from rival_search_mcp.logging.logger import logger


class DataverseDatasetProvider:
    """Search Dataverse datasets (defaults to Harvard's instance)."""

    def __init__(self, instance: str = "dataverse.harvard.edu"):
        self.instance = instance.rstrip("/")
        self.base_url = f"https://{self.instance}"
        self.api_url = f"{self.base_url}/api/search"
        self.headers = {
            "User-Agent": (
                "rivalsearchmcp/1.0 " "(+https://github.com/damionrashford/RivalSearchMCP)"
            ),
            "Accept": "application/json",
        }

    async def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        params = {
            "q": query,
            "type": "dataset",
            "per_page": min(limit, 100),
            "sort": "date",
            "order": "desc",
        }
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                r = await client.get(self.api_url, params=params)
                if r.status_code != 200:
                    logger.warning(
                        "dataverse (%s) returned %s (body: %s)",
                        self.instance,
                        r.status_code,
                        r.text[:200],
                    )
                    return []
                items = r.json().get("data", {}).get("items", [])
                out = [self._format(it) for it in items[:limit]]
                logger.info("dataverse (%s): %d for %r", self.instance, len(out), query)
                return out
        except httpx.HTTPError as e:
            logger.warning("dataverse network error: %s", e)
            return []
        except Exception:
            logger.exception("dataverse unexpected error")
            return []

    def _format(self, item: Dict[str, Any]) -> Dict[str, Any]:
        authors = item.get("authors") or []
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split(";") if a.strip()]
        keywords: Optional[List[str]] = item.get("keywords")
        # Some Dataverse responses return keywords as comma-separated string
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]
        return {
            "id": item.get("global_id") or item.get("entity_id"),
            "title": item.get("name", ""),
            "description": (item.get("description") or "").strip()[:500],
            "owner_name": ", ".join(authors) if authors else item.get("publisher", ""),
            "url": item.get("url", ""),
            "license": "",
            "last_updated": item.get("published_at") or item.get("updatedAt"),
            "doi": (item.get("global_id") or "").replace("doi:", ""),
            "tags": keywords or [],
            "source": f"dataverse:{self.instance}",
        }

    def close(self):
        """Nothing to close; AsyncClient is used per-call."""
