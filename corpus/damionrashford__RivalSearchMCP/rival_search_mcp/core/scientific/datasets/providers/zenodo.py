"""
Zenodo dataset search provider.

Zenodo (zenodo.org) is CERN's open-science repository: datasets,
software, papers, posters, presentations, images, videos, etc. All
records are citable (DOI per record) and most are CC-licensed. No
authentication required for read-only queries.

We restrict to `type=dataset` so the dataset discovery tool stays
focused -- callers who want the other content types can use the
academic search tool instead.
"""

from typing import Any, Dict, List

import httpx

from rival_search_mcp.logging.logger import logger


class ZenodoDatasetProvider:
    """Search Zenodo datasets via the public REST API."""

    def __init__(self):
        self.api_url = "https://zenodo.org/api/records"
        self.headers = {
            "User-Agent": (
                "rivalsearchmcp/1.0 " "(+https://github.com/damionrashford/RivalSearchMCP)"
            ),
            "Accept": "application/json",
        }

    async def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        params = {
            "q": query,
            "size": min(limit, 100),
            "type": "dataset",
            "sort": "bestmatch",
        }
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                r = await client.get(self.api_url, params=params)
                if r.status_code != 200:
                    logger.warning(
                        "zenodo returned %s (body: %s)",
                        r.status_code,
                        r.text[:200],
                    )
                    return []
                hits = r.json().get("hits", {}).get("hits", [])
                out = [self._format(h) for h in hits[:limit]]
                logger.info("zenodo: %d for %r", len(out), query)
                return out
        except httpx.HTTPError as e:
            logger.warning("zenodo network error: %s", e)
            return []
        except Exception:
            logger.exception("zenodo unexpected error")
            return []

    def _format(self, hit: Dict[str, Any]) -> Dict[str, Any]:
        meta = hit.get("metadata") or {}
        creators = meta.get("creators") or []
        owner = creators[0].get("name", "") if creators else ""
        doi = meta.get("doi") or hit.get("doi") or ""
        url = hit.get("links", {}).get("self_html") or (f"https://doi.org/{doi}" if doi else "")
        keywords = meta.get("keywords") or []
        return {
            "id": hit.get("id"),
            "title": meta.get("title", ""),
            "description": (meta.get("description") or "").strip()[:500],
            "owner_name": owner,
            "url": url,
            "license": (meta.get("license") or {}).get("id", ""),
            "download_count": (hit.get("stats") or {}).get("downloads", 0),
            "vote_count": (hit.get("stats") or {}).get("unique_views", 0),
            "last_updated": meta.get("publication_date"),
            "doi": doi,
            "tags": keywords,
            "source": "zenodo",
        }

    def close(self):
        """Nothing to close; AsyncClient is used per-call."""
