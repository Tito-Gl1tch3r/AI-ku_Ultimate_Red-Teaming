"""
CrossRef academic search provider.

CrossRef (api.crossref.org) is the largest metadata registry for
DOI-registered scholarly works -- ~140M works across journals,
books, conference proceedings, datasets, and preprints. No
authentication required. CrossRef asks callers to identify
themselves via a `mailto=` query parameter or UA string for the
"Polite Pool" (faster + separate SLA).

Each result returned includes title, authors, year, venue
(container-title), DOI, and citation count when present.
"""

from typing import Any, Dict, List

import httpx

from rival_search_mcp.logging.logger import logger

_API_BASE = "https://api.crossref.org"
_POLITE_MAILTO = "research@rivalsearchmcp.com"


class CrossRefProvider:
    """Search CrossRef via the public REST API."""

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "rivalsearchmcp/1.0 "
                f"(mailto:{_POLITE_MAILTO}; "
                "+https://github.com/damionrashford/RivalSearchMCP)"
            ),
            "Accept": "application/json",
        }

    async def search(self, query: str, limit: int = 20, **kwargs: Any) -> List[Dict[str, Any]]:
        params = {
            "query": query,
            "rows": min(limit, 100),
            "mailto": _POLITE_MAILTO,
        }
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                r = await client.get(f"{_API_BASE}/works", params=params)
                if r.status_code != 200:
                    logger.warning(
                        "crossref returned %s (body: %s)",
                        r.status_code,
                        r.text[:200],
                    )
                    return []
                items = r.json().get("message", {}).get("items", [])
                papers = [self._format(w) for w in items[:limit]]
                logger.info("crossref: %d for %r", len(papers), query)
                return papers
        except httpx.HTTPError as e:
            logger.warning("crossref network error: %s", e)
            return []
        except Exception:
            logger.exception("crossref unexpected error")
            return []

    def _format(self, work: Dict[str, Any]) -> Dict[str, Any]:
        # CrossRef title + container-title are lists of strings; take first.
        title_list = work.get("title") or []
        title = title_list[0] if title_list else ""
        venue_list = work.get("container-title") or []
        venue = venue_list[0] if venue_list else ""

        authors = []
        for a in work.get("author", []) or []:
            name = " ".join(filter(None, [a.get("given"), a.get("family")])).strip()
            if name:
                authors.append({"name": name})

        # Published date can live in several fields.
        date_parts = (
            (work.get("published-print") or {}).get("date-parts")
            or (work.get("published-online") or {}).get("date-parts")
            or (work.get("issued") or {}).get("date-parts")
            or []
        )
        year = None
        if date_parts and isinstance(date_parts, list) and date_parts[0]:
            try:
                year = int(date_parts[0][0])
            except (TypeError, ValueError):
                year = None

        doi = work.get("DOI", "")
        return {
            "title": title,
            "authors": authors,
            "abstract": (work.get("abstract") or "").strip(),
            "url": work.get("URL") or (f"https://doi.org/{doi}" if doi else ""),
            "year": year,
            "venue": venue,
            "citationCount": work.get("is-referenced-by-count", 0),
            "doi": doi,
            "paperId": doi,
            "type": work.get("type", ""),
            "source": "crossref",
        }

    def close(self):
        """Nothing to close; AsyncClient is used per-call."""
