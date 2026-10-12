"""
Kaggle dataset search provider.

Uses Kaggle's public `/api/v1/datasets/list` endpoint. Most Kaggle
API endpoints require a signed kaggle.json key, but the list
endpoint accepts anonymous queries (returns 400 + "You must accept
the rules of this competition" shape for gated datasets, which we
log at debug and skip).
"""

from typing import Any, Dict, List, Optional

import httpx

from rival_search_mcp.logging.logger import logger

_API_BASE = "https://www.kaggle.com/api/v1"


class KaggleDatasetProvider:
    """Search Kaggle datasets via the public list endpoint."""

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "rivalsearchmcp/1.0 " "(+https://github.com/damionrashford/RivalSearchMCP)"
            ),
            "Accept": "application/json",
        }

    async def search(
        self, query: str, limit: int = 20, sort_by: str = "relevance"
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"search": query, "size": min(limit, 100)}
        sort_map = {
            "hotness": "hotness",
            "votes": "voteCount",
            "updated": "lastUpdated",
        }
        if sort_by in sort_map:
            params["sortBy"] = sort_map[sort_by]

        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                r = await client.get(f"{_API_BASE}/datasets/list", params=params)
                if r.status_code == 400:
                    logger.debug(
                        "kaggle list endpoint 400 -- anonymous queries sometimes "
                        "refused; other sources will fill in"
                    )
                    return []
                if r.status_code != 200:
                    logger.warning(
                        "kaggle returned %s (body: %s)",
                        r.status_code,
                        r.text[:200],
                    )
                    return []
                datasets = r.json() or []
                out = [self._format(d) for d in datasets[:limit]]
                logger.info("kaggle: %d for %r", len(out), query)
                return out
        except httpx.HTTPError as e:
            logger.warning("kaggle network error: %s", e)
            return []
        except Exception:
            logger.exception("kaggle unexpected error")
            return []

    def _format(self, ds: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": ds.get("id"),
            "title": ds.get("title") or ds.get("titleNullable") or "",
            "description": ds.get("subtitle") or ds.get("subtitleNullable") or "",
            "owner_name": ds.get("ownerName") or ds.get("ownerNameNullable") or "",
            "url": ds.get("url") or ds.get("urlNullable") or "",
            "license": ds.get("licenseName") or ds.get("licenseNameNullable") or "",
            "size_bytes": ds.get("totalBytes") or ds.get("totalBytesNullable"),
            "download_count": ds.get("downloadCount", 0),
            "vote_count": ds.get("voteCount", 0),
            "last_updated": ds.get("lastUpdated"),
            "tags": [tag.get("name", "") for tag in ds.get("tags", []) if tag.get("name")],
            "source": "kaggle",
        }

    async def get_dataset_details(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        if "/" not in dataset_id:
            logger.warning("kaggle: invalid dataset_id format %r", dataset_id)
            return None
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                r = await client.get(f"{_API_BASE}/datasets/view/{dataset_id}")
                if r.status_code != 200:
                    return None
                return self._format(r.json())
        except Exception:
            logger.exception("kaggle get_dataset_details failed")
            return None

    def close(self):
        """Nothing to close; AsyncClient is used per-call."""
