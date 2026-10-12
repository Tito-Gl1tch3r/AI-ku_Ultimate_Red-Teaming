"""
Europe PMC academic search provider.

Europe PMC (ebi.ac.uk/europepmc) indexes biomedical and life-sciences
literature, mirroring PubMed plus a significant amount of non-NCBI
content (bioRxiv/medRxiv preprints, agricultural research, patents,
theses). No authentication required. The REST API's `resultType=core`
parameter returns full metadata including authors, abstract, journal,
citation count, and open-access PDF link when available.

Ideal as a complement to PubMed: PubMed is NCBI-only; Europe PMC
federates many additional biomed sources.
"""

from typing import Any, Dict, List

import httpx

from rival_search_mcp.logging.logger import logger

_API_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"


class EuropePMCProvider:
    """Search Europe PMC via the public REST API."""

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "rivalsearchmcp/1.0 " "(+https://github.com/damionrashford/RivalSearchMCP)"
            ),
            "Accept": "application/json",
        }

    async def search(self, query: str, limit: int = 20, **kwargs: Any) -> List[Dict[str, Any]]:
        params = {
            "query": query,
            "resultType": "core",
            "format": "json",
            "pageSize": min(limit, 100),
        }
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                r = await client.get(f"{_API_BASE}/search", params=params)
                if r.status_code != 200:
                    logger.warning(
                        "europepmc returned %s (body: %s)",
                        r.status_code,
                        r.text[:200],
                    )
                    return []
                result_list = r.json().get("resultList", {}).get("result", [])
                papers = [self._format(w) for w in result_list[:limit]]
                logger.info("europepmc: %d for %r", len(papers), query)
                return papers
        except httpx.HTTPError as e:
            logger.warning("europepmc network error: %s", e)
            return []
        except Exception:
            logger.exception("europepmc unexpected error")
            return []

    def _format(self, work: Dict[str, Any]) -> Dict[str, Any]:
        # Europe PMC `authorString` is comma-separated; split so the shape
        # matches the other providers.
        author_string = work.get("authorString") or ""
        authors = [{"name": name.strip()} for name in author_string.split(",") if name.strip()]

        # Find a usable URL: DOI first, then the Europe PMC canonical.
        doi = work.get("doi", "")
        pmid = work.get("pmid", "")
        europmc_id = work.get("id", "")
        europmc_source = work.get("source", "")
        if doi:
            url = f"https://doi.org/{doi}"
        elif pmid:
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        elif europmc_source and europmc_id:
            url = f"https://europepmc.org/article/" f"{europmc_source}/{europmc_id}"
        else:
            url = ""

        pdf_url = ""
        for full_text in (work.get("fullTextUrlList") or {}).get("fullTextUrl", []):
            if (full_text.get("documentStyle") or "").lower() == "pdf":
                pdf_url = full_text.get("url", "")
                break

        year_raw = work.get("pubYear")
        year = int(year_raw) if year_raw and str(year_raw).isdigit() else None

        return {
            "title": work.get("title", ""),
            "authors": authors,
            "abstract": work.get("abstractText", ""),
            "url": url,
            "pdf_url": pdf_url,
            "year": year,
            "venue": work.get("journalTitle", ""),
            "citationCount": work.get("citedByCount", 0),
            "doi": doi,
            "paperId": pmid or f"{europmc_source}:{europmc_id}",
            "source": "europepmc",
        }

    def close(self):
        """Nothing to close; AsyncClient is used per-call."""
