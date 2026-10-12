"""
OpenAlex academic search provider.

OpenAlex (api.openalex.org) is a free, open-access catalog of ~240M
scholarly works, authors, institutions, and concepts. It is the
spiritual successor to Microsoft Academic Graph after MAG was
retired in 2021. No authentication required; including a `mailto`
parameter routes the request to the higher-throughput "polite pool".

Each work returned includes title, authors, year, venue (host
venue), citation count, abstract (reconstructed from inverted
index), DOI, and open-access PDF URL when available.
"""

from typing import Any, Dict, List

import httpx

from rival_search_mcp.logging.logger import logger

_API_BASE = "https://api.openalex.org"
_POLITE_MAILTO = "research@rivalsearchmcp.com"


def _abstract_from_inverted_index(idx: Dict[str, List[int]]) -> str:
    """Reconstruct the abstract from OpenAlex's inverted-index storage.

    OpenAlex returns abstracts as {word: [position, position, ...]}
    for size reasons. Invert that back to plain text.
    """
    if not idx:
        return ""
    positions: List[str] = []
    for word, indices in idx.items():
        for i in indices:
            while len(positions) <= i:
                positions.append("")
            positions[i] = word
    return " ".join(w for w in positions if w)


class OpenAlexProvider:
    """Search OpenAlex via the public REST API."""

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "rivalsearchmcp/1.0 " "(+https://github.com/damionrashford/RivalSearchMCP)"
            ),
            "Accept": "application/json",
        }

    async def search(self, query: str, limit: int = 20, **kwargs: Any) -> List[Dict[str, Any]]:
        params = {
            "search": query,
            "per-page": min(limit, 200),
            "mailto": _POLITE_MAILTO,
        }
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                r = await client.get(f"{_API_BASE}/works", params=params)
                if r.status_code != 200:
                    logger.warning(
                        "openalex returned %s (body: %s)",
                        r.status_code,
                        r.text[:200],
                    )
                    return []
                results = r.json().get("results", [])
                papers = [self._format(w) for w in results[:limit]]
                logger.info("openalex: %d for %r", len(papers), query)
                return papers
        except httpx.HTTPError as e:
            logger.warning("openalex network error: %s", e)
            return []
        except Exception:
            logger.exception("openalex unexpected error")
            return []

    def _format(self, work: Dict[str, Any]) -> Dict[str, Any]:
        authors = []
        for a in work.get("authorships", []):
            name = (a.get("author") or {}).get("display_name")
            if name:
                authors.append({"name": name})

        host_venue = work.get("host_venue") or {}
        oa = work.get("open_access") or {}
        pdf_url = oa.get("oa_url") or ""

        return {
            "title": work.get("title") or "",
            "authors": authors,
            "abstract": _abstract_from_inverted_index(work.get("abstract_inverted_index") or {}),
            "url": work.get("doi") or work.get("id") or "",
            "pdf_url": pdf_url,
            "year": work.get("publication_year"),
            "venue": host_venue.get("display_name", ""),
            "citationCount": work.get("cited_by_count", 0),
            "doi": (work.get("doi") or "").replace("https://doi.org/", ""),
            "paperId": (work.get("id") or "").rsplit("/", 1)[-1],
            "source": "openalex",
        }

    def close(self):
        """Nothing to close; AsyncClient is used per-call."""
