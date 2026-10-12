"""
arXiv academic search provider via the public arXiv Atom XML API.

No authentication required. Rate-limited by the arXiv team to "a few
requests per second" per IP. Covers ~2.4M preprints across CS, math,
physics, quant-bio, quant-fin, stats, and EESS.
"""

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import httpx

from rival_search_mcp.logging.logger import logger

_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
_ARXIV_API = "http://export.arxiv.org/api/query"


class ArXivProvider:
    """Search arXiv preprints via the public Atom API."""

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "rivalsearchmcp/1.0 " "(+https://github.com/damionrashford/RivalSearchMCP)"
            ),
        }

    async def search(
        self,
        query: str,
        limit: int = 20,
        sort_by: str = "relevance",
        sort_order: str = "descending",
    ) -> List[Dict[str, Any]]:
        params = {
            "search_query": query,
            "start": 0,
            "max_results": min(limit, 200),
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                r = await client.get(_ARXIV_API, params=params)
                if r.status_code != 200:
                    logger.warning("arXiv returned %s for %r", r.status_code, query)
                    return []
                papers = self._parse(r.text, limit)
                logger.info("arxiv: %d papers for %r", len(papers), query)
                return papers
        except httpx.HTTPError as e:
            logger.warning("arxiv network error: %s", e)
            return []
        except Exception:
            logger.exception("arxiv unexpected error")
            return []

    def _parse(self, xml_content: str, limit: int) -> List[Dict[str, Any]]:
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            logger.warning("arxiv XML parse failed: %s", e)
            return []

        papers: List[Dict[str, Any]] = []
        for entry in root.findall("atom:entry", _ATOM_NS)[:limit]:
            try:
                title = _text(entry.find("atom:title", _ATOM_NS))
                url = _text(entry.find("atom:id", _ATOM_NS))
                abstract = _text(entry.find("atom:summary", _ATOM_NS))
                published = _text(entry.find("atom:published", _ATOM_NS))
                authors = [
                    {"name": _text(a.find("atom:name", _ATOM_NS))}
                    for a in entry.findall("atom:author", _ATOM_NS)
                ]
                authors = [a for a in authors if a["name"]]
                papers.append(
                    {
                        "title": title,
                        "authors": authors,
                        "abstract": abstract,
                        "url": url,
                        "year": published[:4] if published else None,
                        "source": "arxiv",
                        "paperId": url.rsplit("/", 1)[-1] if url else None,
                    }
                )
            except Exception as e:
                logger.debug("arxiv entry parse failed: %s", e)
        return papers

    async def get_paper_details(self, paper_id: str) -> Optional[Dict[str, Any]]:
        params = {"id_list": paper_id}
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                r = await client.get(_ARXIV_API, params=params)
                if r.status_code != 200:
                    return None
                papers = self._parse(r.text, 1)
                return papers[0] if papers else None
        except Exception:
            logger.exception("arxiv get_paper_details failed")
            return None

    def close(self):
        """Nothing to close; AsyncClient is used per-call."""


def _text(elem) -> str:
    """Safely extract stripped text from an ElementTree element."""
    if elem is None or elem.text is None:
        return ""
    return elem.text.strip()
