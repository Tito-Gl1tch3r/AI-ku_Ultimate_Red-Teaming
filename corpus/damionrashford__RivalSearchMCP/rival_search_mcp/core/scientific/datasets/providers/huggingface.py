"""
HuggingFace Hub dataset search provider.

Public `/api/datasets` endpoint; no authentication required.
Supports full-text search via the `search` query parameter and
returns up to 100 dataset records with downloads, likes, tags,
and last-modified timestamps.
"""

from typing import Any, Dict, List, Optional

import httpx

from rival_search_mcp.logging.logger import logger

_API_BASE = "https://huggingface.co/api"


class HuggingFaceDatasetProvider:
    """Search HuggingFace Hub datasets."""

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "rivalsearchmcp/1.0 " "(+https://github.com/damionrashford/RivalSearchMCP)"
            ),
            "Accept": "application/json",
        }

    async def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        params = {"search": query, "limit": min(limit, 100)}
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                r = await client.get(f"{_API_BASE}/datasets", params=params)
                if r.status_code != 200:
                    logger.warning(
                        "huggingface returned %s (body: %s)",
                        r.status_code,
                        r.text[:200],
                    )
                    return []
                datasets = r.json() or []
                out = [self._format(d) for d in datasets[:limit]]
                logger.info("huggingface: %d for %r", len(out), query)
                return out
        except httpx.HTTPError as e:
            logger.warning("huggingface network error: %s", e)
            return []
        except Exception:
            logger.exception("huggingface unexpected error")
            return []

    def _format(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        ds_id = dataset.get("id", "")
        title = ds_id.split("/")[-1] if ds_id else ""
        description = (dataset.get("description") or "").strip()[:500]
        return {
            "id": ds_id,
            "title": title,
            "description": description,
            "author": dataset.get("author"),
            "url": f"https://huggingface.co/datasets/{ds_id}" if ds_id else "",
            "downloads": dataset.get("downloads", 0),
            "likes": dataset.get("likes", 0),
            "last_modified": dataset.get("lastModified"),
            "tags": dataset.get("tags", []),
            "source": "huggingface",
        }

    async def get_dataset_details(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                r = await client.get(f"{_API_BASE}/datasets/{dataset_id}")
                if r.status_code != 200:
                    return None
                data = r.json()
                formatted = self._format(data)
                formatted["card_data"] = data.get("cardData")
                return formatted
        except Exception:
            logger.exception("huggingface get_dataset_details failed")
            return None

    def close(self):
        """Nothing to close; AsyncClient is used per-call."""
