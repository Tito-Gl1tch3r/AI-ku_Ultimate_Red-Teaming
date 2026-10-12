"""
Analysis tools for FastMCP server.
Handles content analysis and end-to-end research workflows.
"""

import asyncio
import re
from typing import Annotated, Any, Dict, List, Literal, Optional, Set

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools.tool import ToolResult
from pydantic import Field

from rival_search_mcp.core.conflict import find_conflicts as _find_conflicts_core
from rival_search_mcp.core.quality import assess_results, summarize_quality
from rival_search_mcp.logging.logger import logger
from rival_search_mcp.utils.markdown_formatter import format_research_analysis_markdown

_RETRIEVE_LIMIT = 20_000

ContentOperation = Literal[
    "retrieve",
    "stream",
    "analyze",
    "extract",
    "score",
    "find_conflicts",
    "validate",
    "bibliography",
]
BibFormat = Literal["apa7", "bibtex", "chicago", "json"]
ExtractionMethod = Literal["auto", "html", "text", "markdown"]
AnalysisType = Literal["general", "sentiment", "technical", "business"]
LinkType = Literal["all", "internal", "external", "images", "documents"]
ResearchMode = Literal["topic", "entity"]


def register_analysis_tools(mcp: FastMCP):
    """Register consolidated content operations tool."""

    @mcp.tool(
        annotations={
            "title": "Content Operations",
            "readOnlyHint": True,
            "openWorldHint": True,
            "destructiveHint": False,
            "idempotentHint": False,
        },
        timeout=90.0,
    )
    async def content_operations(
        operation: Annotated[
            ContentOperation,
            Field(
                description=(
                    "What to do:\n"
                    "  retrieve       - fetch `url` and return its text/html/markdown\n"
                    "  stream         - stream-fetch `url`\n"
                    "  analyze        - analyze `content` for key points / sentiment\n"
                    "  extract        - extract links from `url`\n"
                    "  score          - rate `urls` on quality signals\n"
                    "  find_conflicts - compare `urls` for numeric / date / polarity disagreements\n"
                    "  validate       - bulk check `urls` (≤100) for liveness, redirects, paywalls, last-modified\n"
                    "  bibliography   - format `sources` as citations; use `bib_format` for style (apa7/bibtex/chicago/json)"
                ),
            ),
        ],
        url: Annotated[
            Optional[str],
            Field(
                description="Single URL for retrieve / stream / extract.",
                default=None,
            ),
        ] = None,
        urls: Annotated[
            Optional[List[str]],
            Field(
                description=(
                    "List of URLs for score (≤50), find_conflicts (2-10), or validate (≤100). "
                    "Ignored for single-URL operations."
                ),
                default=None,
            ),
        ] = None,
        content: Annotated[
            Optional[str],
            Field(
                description="Content body for `analyze` operation.",
                default=None,
            ),
        ] = None,
        claim: Annotated[
            Optional[str],
            Field(
                description=(
                    "find_conflicts only: a specific claim to check for "
                    "support vs contradiction across `urls` (e.g. 'the "
                    "vaccine is safe')."
                ),
                default=None,
            ),
        ] = None,
        metadata: Annotated[
            Optional[List[Dict[str, Any]]],
            Field(
                description=(
                    "score only: per-URL metadata aligned with `urls` "
                    "(title, published, citationCount, etc.) to sharpen "
                    "the freshness and corroboration signals."
                ),
                default=None,
            ),
        ] = None,
        extraction_method: Annotated[
            ExtractionMethod,
            Field(
                description="retrieve only: output format.",
                default="auto",
            ),
        ] = "auto",
        analysis_type: Annotated[
            AnalysisType,
            Field(description="analyze only: analysis focus.", default="general"),
        ] = "general",
        max_links: Annotated[
            int,
            Field(description="extract only: max links returned.", default=100, ge=1, le=500),
        ] = 100,
        link_type: Annotated[
            LinkType,
            Field(description="extract only: which link category.", default="all"),
        ] = "all",
        extract_key_points: Annotated[
            bool,
            Field(description="analyze only: extract key points.", default=True),
        ] = True,
        summarize: Annotated[
            bool,
            Field(description="analyze only: produce a summary.", default=True),
        ] = True,
        include_metadata: Annotated[
            bool,
            Field(description="Include metadata in the response.", default=True),
        ] = True,
        bib_format: Annotated[
            BibFormat,
            Field(description="bibliography only: output style.", default="apa7"),
        ] = "apa7",
        sources: Annotated[
            Optional[List[Dict[str, Any]]],
            Field(
                description=(
                    "bibliography only: list of source objects to format. "
                    "Each object may contain: url, title, authors (list), year, "
                    "journal, volume, issue, pages, doi, publisher, accessed_date. "
                    "Any subset is accepted; missing fields are omitted from the citation."
                ),
                default=None,
            ),
        ] = None,
        ctx: Optional[Context] = None,
    ) -> ToolResult | str:
        """
        One tool for every URL/content-level operation. Pick `operation`,
        provide whichever of `url`, `urls`, `content` that operation
        needs, and leave the rest defaulted. Parameter annotations above
        (visible in the MCP schema) state which operation each parameter
        applies to.

        Quick map of operation -> required inputs:

          retrieve       url
          stream         url
          analyze        content
          extract        url
          score          urls              (optionally metadata)
          find_conflicts urls              (optionally claim)
          validate       urls              (≤100 URLs; checks liveness, redirects, paywalls, last-modified)
        """
        try:
            logger.info(f"Performing {operation} operation")

            if operation == "retrieve":
                if not url:
                    raise ToolError("URL required for retrieve operation")

                from rival_search_mcp.utils.scrapling_client import (
                    fetch_html,
                    fetch_markdown,
                    fetch_text,
                )

                max_retries = 3
                result: Optional[str] = None
                for attempt in range(max_retries):
                    try:
                        if extraction_method == "html":
                            result = await fetch_html(url)
                        elif extraction_method == "text":
                            result = await fetch_text(url)
                        else:
                            result = await fetch_markdown(url)
                        if result:
                            break
                    except Exception as e:
                        logger.warning(f"Content retrieval attempt {attempt + 1} failed: {e}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)

                if not result:
                    result = (
                        f"Failed to retrieve content from {url} after " f"{max_retries} attempts"
                    )
                    return result

                if len(result) > _RETRIEVE_LIMIT:
                    total = len(result)
                    result = (
                        f"[truncated: {total:,} chars retrieved, showing first {_RETRIEVE_LIMIT:,}]\n\n"
                        + result[:_RETRIEVE_LIMIT]
                    )
                return result

            elif operation == "stream":
                if not url:
                    raise ToolError("URL required for stream operation")
                from rival_search_mcp.core.fetch import stream_fetch

                max_retries = 3
                content = None
                for attempt in range(max_retries):
                    try:
                        content = await stream_fetch(url)
                        if content:
                            break
                    except Exception as e:
                        logger.warning(f"Content streaming attempt {attempt + 1} failed: {e}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1)

                if content:
                    result = str(content)
                else:
                    result = f"Failed to stream content from {url} after {max_retries} attempts"

                return result

            elif operation == "analyze":
                if not content:
                    raise ToolError("Content required for analyze operation")

                analysis_result: Dict[str, Any] = {
                    "content_length": len(content),
                    "word_count": len(content.split()),
                    "analysis_type": analysis_type,
                    "key_points": [],
                    "summary": "",
                    "insights": {},
                }

                if extract_key_points:
                    sentences = re.split(r"[.!?]+", content)
                    sentences = [s.strip() for s in sentences if len(s.strip()) > 30]

                    scored_sentences = []
                    for sentence in sentences:
                        score = len(sentence) * 0.3
                        important_words = [
                            "important",
                            "key",
                            "critical",
                            "essential",
                            "significant",
                            "major",
                            "primary",
                        ]
                        for word in important_words:
                            if word.lower() in sentence.lower():
                                score += 10
                        scored_sentences.append((sentence, score))

                    scored_sentences.sort(key=lambda x: x[1], reverse=True)
                    key_points = [s[0] for s in scored_sentences[:5]]
                    analysis_result["key_points"] = key_points

                if summarize:
                    sentences = re.split(r"[.!?]+", content)
                    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

                    if len(sentences) > 3:
                        summary_parts = [
                            sentences[0],
                            sentences[len(sentences) // 2] if len(sentences) > 2 else "",
                            sentences[-1] if len(sentences) > 1 else "",
                        ]
                        summary = ". ".join([s for s in summary_parts if s])
                    else:
                        summary = content

                    analysis_result["summary"] = summary

                if analysis_type == "sentiment":
                    positive_words = [
                        "good",
                        "great",
                        "excellent",
                        "amazing",
                        "wonderful",
                        "positive",
                        "happy",
                        "success",
                    ]
                    negative_words = [
                        "bad",
                        "terrible",
                        "awful",
                        "negative",
                        "sad",
                        "failure",
                        "problem",
                        "issue",
                    ]

                    content_lower = content.lower()
                    positive_count = sum(content_lower.count(word) for word in positive_words)
                    negative_count = sum(content_lower.count(word) for word in negative_words)

                    sentiment = (
                        "positive"
                        if positive_count > negative_count
                        else "negative" if negative_count > positive_count else "neutral"
                    )
                    analysis_result["insights"]["sentiment"] = sentiment

                elif analysis_type == "technical":
                    technical_patterns = [
                        r"\b[A-Z]{2,}\b",
                        r"\b\w+\.\w+\b",
                        r"\b\d+\.\d+\b",
                        r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b",
                    ]
                    technical_terms = set()
                    for pattern in technical_patterns:
                        matches = re.findall(pattern, content)
                        technical_terms.update(matches)
                    analysis_result["insights"]["technical_terms"] = list(technical_terms)[:10]

                elif analysis_type == "business":
                    money_pattern = r"\$[\d,]+(?:\.\d{2})?"
                    percentage_pattern = r"\d+(?:\.\d+)?%"
                    date_pattern = r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
                    money_matches = re.findall(money_pattern, content)
                    percentage_matches = re.findall(percentage_pattern, content)
                    date_matches = re.findall(date_pattern, content)
                    analysis_result["insights"]["business_metrics"] = {
                        "monetary_values": money_matches[:5],
                        "percentages": percentage_matches[:5],
                        "dates": date_matches[:5],
                    }

                return format_research_analysis_markdown(
                    {
                        "topic": f"Content Analysis: {content[:50]}{'...' if len(content) > 50 else ''}",
                        "summary": analysis_result.get("summary", ""),
                        "key_findings": analysis_result.get("key_points", []),
                        "status": "success",
                    },
                    "Content Operations",
                )

            elif operation == "extract":
                if not url:
                    raise ToolError("URL required for extract operation")

                # Real link extraction implementation
                from urllib.parse import urljoin, urlparse

                from rival_search_mcp.core.fetch import base_fetch_url

                try:
                    content = await base_fetch_url(url)
                    if not content:
                        return format_research_analysis_markdown(
                            {
                                "topic": f"Link Extraction from {url}",
                                "status": "error",
                                "error": "Failed to fetch content",
                            },
                            "Content Operations",
                        )

                    from scrapling.parser import Selector

                    sel = Selector(content=str(content))

                    all_links = []
                    internal_links = []
                    external_links = []
                    image_links = []
                    document_links = []

                    base_domain = urlparse(url).netloc

                    for a_el in sel.css("a[href]"):
                        href = str(a_el.attrib.get("href", ""))
                        if not href or href.startswith("#"):
                            continue

                        absolute_url = urljoin(url, href)
                        link_domain = urlparse(absolute_url).netloc

                        link_info = {
                            "url": absolute_url,
                            "text": a_el.get_all_text(strip=True)[:100] or "No text",
                            "type": "internal" if link_domain == base_domain else "external",
                        }

                        all_links.append(link_info)

                        if link_domain == base_domain:
                            internal_links.append(link_info)
                        else:
                            external_links.append(link_info)

                        if any(
                            absolute_url.lower().endswith(ext)
                            for ext in [
                                ".pdf",
                                ".doc",
                                ".docx",
                                ".xls",
                                ".xlsx",
                                ".ppt",
                                ".pptx",
                                ".zip",
                            ]
                        ):
                            document_links.append(link_info)

                    for img_el in sel.css("img[src]"):
                        src = str(img_el.attrib.get("src", ""))
                        absolute_url = urljoin(url, src)
                        image_links.append(
                            {
                                "url": absolute_url,
                                "alt": str(img_el.attrib.get("alt", "No alt text")),
                                "type": "image",
                            }
                        )

                    if link_type == "internal":
                        selected_links = internal_links
                    elif link_type == "external":
                        selected_links = external_links
                    elif link_type == "images":
                        selected_links = image_links
                    elif link_type == "documents":
                        selected_links = document_links
                    else:
                        selected_links = all_links

                    selected_links = selected_links[:max_links]

                    result_summary = f"Extracted {len(selected_links)} {link_type} links from {url}"
                    key_findings = [
                        f"{link.get('text', link.get('alt', 'Link'))}: {link['url']}"
                        for link in selected_links[:10]
                    ]

                    if link_type == "all":
                        result_summary += f" ({len(internal_links)} internal, {len(external_links)} external, {len(image_links)} images, {len(document_links)} documents)"

                    return format_research_analysis_markdown(
                        {
                            "topic": f"Link Extraction: {url}",
                            "summary": result_summary,
                            "key_findings": key_findings,
                            "link_statistics": {
                                "total_links": len(all_links),
                                "internal_links": len(internal_links),
                                "external_links": len(external_links),
                                "image_links": len(image_links),
                                "document_links": len(document_links),
                                "extracted_type": link_type,
                                "extracted_count": len(selected_links),
                            },
                            "status": "success",
                        },
                        "Content Operations",
                    )

                except Exception as extract_error:
                    logger.error(f"Link extraction failed: {extract_error}")
                    return format_research_analysis_markdown(
                        {
                            "topic": f"Link Extraction from {url}",
                            "status": "error",
                            "error": str(extract_error),
                        },
                        "Content Operations",
                    )

            elif operation == "score":
                if not urls:
                    raise ToolError("urls list required for score operation")
                if len(urls) > 50:
                    raise ToolError("score operation accepts at most 50 urls")

                md = list(metadata or [])
                while len(md) < len(urls):
                    md.append({})
                seeded = [{"url": u, **(m or {})} for u, m in zip(urls, md)]
                annotated = assess_results(seeded)
                quality_summary = summarize_quality(annotated)

                score_findings = [
                    f"{r['quality']['score']}/100 ({r['quality']['tier']}) — {r['url']}"
                    for r in annotated
                ]
                payload = {
                    "topic": "Source Quality Scores",
                    "summary": (
                        f"Confidence {quality_summary['confidence']} · "
                        f"mean {quality_summary['mean_score']}/100 · "
                        f"{quality_summary['independent_domains']} independent domains across "
                        f"{quality_summary['result_count']} sources"
                    ),
                    "key_findings": score_findings,
                    "quality_details": [{"url": r["url"], **r["quality"]} for r in annotated],
                    "confidence": quality_summary,
                    "status": "success",
                }
                return ToolResult(
                    content=format_research_analysis_markdown(payload, "Content Operations"),
                    structured_content=payload,
                )

            elif operation == "find_conflicts":
                if not urls or len(urls) < 2:
                    raise ToolError("find_conflicts requires a list of at least 2 urls")
                if len(urls) > 10:
                    raise ToolError("find_conflicts accepts at most 10 urls per call")

                # Scrapling first for TLS fingerprint, httpx fallback. Cap
                # at 8000 chars/source so the detector doesn't drown in noise.
                from scrapling.fetchers import AsyncFetcher

                from rival_search_mcp.core.content.extractors import UnifiedContentExtractor

                extractor = UnifiedContentExtractor()

                fetch_total = len(urls)
                fetched = 0

                async def _snippet(target_url: str) -> str:
                    nonlocal fetched
                    try:
                        try:
                            page = await AsyncFetcher.get(
                                target_url, stealthy_headers=True, timeout=20
                            )
                            if page.status == 200 and page.body:
                                text = page.text or page.body.decode("utf-8", "replace")
                                return extractor.extract(text)[:8000]
                        except Exception as e:
                            logger.debug(
                                "find_conflicts Scrapling fetch failed for %s: %s",
                                target_url,
                                e,
                            )
                        try:
                            import httpx

                            async with httpx.AsyncClient(
                                timeout=20.0,
                                follow_redirects=True,
                                headers={"User-Agent": "rivalsearchmcp/1.0"},
                            ) as client:
                                r = await client.get(target_url)
                                if r.status_code == 200:
                                    return extractor.extract(r.text)[:8000]
                        except Exception as e:
                            logger.warning("find_conflicts fetch failed for %s: %s", target_url, e)
                        return ""
                    finally:
                        fetched += 1
                        if ctx is not None:
                            try:
                                await ctx.report_progress(
                                    progress=fetched,
                                    total=fetch_total,
                                    message=f"fetched {fetched}/{fetch_total} sources",
                                )
                            except Exception:
                                pass

                if ctx is not None:
                    try:
                        await ctx.report_progress(
                            progress=0,
                            total=fetch_total,
                            message=f"fetching {fetch_total} sources",
                        )
                    except Exception:
                        pass
                snippets = await asyncio.gather(*[_snippet(u) for u in urls])
                if ctx is not None:
                    try:
                        await ctx.report_progress(
                            progress=fetch_total,
                            total=fetch_total,
                            message="detecting conflicts",
                        )
                    except Exception:
                        pass
                report = _find_conflicts_core([s for s in snippets], claim=claim)

                findings = []
                for c in report.conflicts:
                    findings.append(
                        f"[{c.type.value}] {c.topic} — "
                        f"{c.value_a} (src {c.source_a_index}) vs "
                        f"{c.value_b} (src {c.source_b_index}) — confidence {c.confidence:.0%}"
                    )
                if not findings:
                    findings = ["No conflicts detected across the provided sources."]

                payload = {
                    "topic": (
                        f"Conflict Analysis ({len(urls)} sources)"
                        + (f" — claim: {claim!r}" if claim else "")
                    ),
                    "summary": (
                        f"{len(report.conflicts)} disagreement(s) detected "
                        f"across {len(urls)} sources. "
                        f"{len(report.agreements)} agreement record(s)."
                    ),
                    "key_findings": findings,
                    "sources": [{"title": url, "url": url} for url in urls],
                    "conflicts": [c.as_dict() for c in report.conflicts],
                    "agreements": report.agreements,
                    "status": "success",
                }
                return ToolResult(
                    content=format_research_analysis_markdown(payload, "Content Operations"),
                    structured_content=payload,
                )

            elif operation == "validate":
                if not urls:
                    raise ToolError("urls required for validate operation")
                if len(urls) > 100:
                    raise ToolError("validate accepts at most 100 URLs per call")

                import httpx as _httpx

                _PAYWALL_PATTERNS = re.compile(
                    r"(login|signin|subscribe|paywall|account|register|checkout|"
                    r"membership|access-denied|gate|metered)",
                    re.IGNORECASE,
                )

                async def _check_url(target: str) -> Dict[str, Any]:
                    result: Dict[str, Any] = {
                        "url": target,
                        "status": None,
                        "redirected": False,
                        "final_url": target,
                        "paywall": False,
                        "last_modified": None,
                        "error": None,
                    }
                    try:
                        async with _httpx.AsyncClient(
                            timeout=10.0,
                            follow_redirects=True,
                            headers={
                                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                            },
                        ) as client:
                            resp = await client.head(target)
                            result["status"] = resp.status_code
                            result["final_url"] = str(resp.url)
                            result["redirected"] = str(resp.url) != target
                            result["last_modified"] = resp.headers.get("last-modified")
                            if resp.status_code == 200:
                                result["paywall"] = bool(
                                    _PAYWALL_PATTERNS.search(result["final_url"])
                                )
                            # Some servers reject HEAD; retry with GET on 405
                            if resp.status_code == 405:
                                resp2 = await client.get(target, headers={"Range": "bytes=0-0"})
                                result["status"] = resp2.status_code
                                result["final_url"] = str(resp2.url)
                                result["redirected"] = str(resp2.url) != target
                                result["last_modified"] = resp2.headers.get("last-modified")
                                if resp2.status_code in (200, 206):
                                    result["paywall"] = bool(
                                        _PAYWALL_PATTERNS.search(result["final_url"])
                                    )
                    except Exception as exc:
                        result["error"] = str(exc)
                    return result

                check_results: List[Dict[str, Any]] = list(
                    await asyncio.gather(*[_check_url(u) for u in urls])
                )

                live = sum(
                    1
                    for r in check_results
                    if r["status"] and 200 <= r["status"] < 400 and not r["paywall"]
                )
                dead = sum(1 for r in check_results if r["status"] and r["status"] >= 400)
                paywalled = sum(1 for r in check_results if r["paywall"])
                errored = sum(1 for r in check_results if r["error"] and not r["status"])

                payload = {
                    "topic": f"URL Validation ({len(urls)} URLs)",
                    "summary": (
                        f"{len(urls)} URLs checked: {live} live, {dead} dead/error-status, "
                        f"{paywalled} paywalled, {errored} network error."
                    ),
                    "results": check_results,
                    "summary_counts": {
                        "live": live,
                        "dead": dead,
                        "paywalled": paywalled,
                        "errored": errored,
                        "total": len(urls),
                    },
                    "status": "success",
                }
                return ToolResult(
                    content=format_research_analysis_markdown(payload, "Content Operations"),
                    structured_content=payload,
                )

            elif operation == "bibliography":
                if not sources:
                    raise ToolError(
                        "bibliography requires `sources` — pass a list of source objects "
                        "(url, title, authors, year, journal, doi, etc.)"
                    )

                import json as _json
                from datetime import date as _date

                today = _date.today().isoformat()

                def _fmt_authors(raw: Any) -> str:
                    if not raw:
                        return "Unknown Author"
                    if isinstance(raw, str):
                        return raw
                    lst = list(raw)
                    if len(lst) == 1:
                        return lst[0]
                    if len(lst) == 2:
                        return f"{lst[0]} & {lst[1]}"
                    return f"{lst[0]} et al."

                def _apa7(s: Dict[str, Any], idx: int) -> str:
                    authors = _fmt_authors(s.get("authors"))
                    year = s.get("year", "n.d.")
                    title = s.get("title", "Untitled")
                    journal = s.get("journal") or s.get("publisher")
                    vol = s.get("volume")
                    issue = s.get("issue")
                    pages = s.get("pages")
                    doi = s.get("doi")
                    url = s.get("url")
                    accessed = s.get("accessed_date", today)

                    line = f"{authors} ({year}). {title}."
                    if journal:
                        line += f" *{journal}*"
                        if vol:
                            line += f", *{vol}*"
                            if issue:
                                line += f"({issue})"
                        if pages:
                            line += f", {pages}"
                        line += "."
                    if doi:
                        line += f" https://doi.org/{doi}"
                    elif url:
                        line += f" Retrieved {accessed}, from {url}"
                    return line

                def _bibtex(s: Dict[str, Any], idx: int) -> str:
                    key = re.sub(r"\W+", "", (s.get("title") or f"ref{idx}").split()[0].lower())
                    year = s.get("year", "")
                    entry_type = "article" if s.get("journal") else "misc"
                    lines = [f"@{entry_type}{{{key}{year},"]
                    authors_raw = s.get("authors")
                    if authors_raw:
                        authors_str = (
                            " and ".join(authors_raw)
                            if isinstance(authors_raw, list)
                            else str(authors_raw)
                        )
                        lines.append(f"  author = {{{authors_str}}},")
                    if s.get("title"):
                        lines.append(f"  title = {{{s['title']}}},")
                    if year:
                        lines.append(f"  year = {{{year}}},")
                    if s.get("journal"):
                        lines.append(f"  journal = {{{s['journal']}}},")
                    if s.get("volume"):
                        lines.append(f"  volume = {{{s['volume']}}},")
                    if s.get("issue"):
                        lines.append(f"  number = {{{s['issue']}}},")
                    if s.get("pages"):
                        lines.append(f"  pages = {{{s['pages']}}},")
                    if s.get("doi"):
                        lines.append(f"  doi = {{{s['doi']}}},")
                    if s.get("url"):
                        lines.append(f"  url = {{{s['url']}}},")
                    if s.get("publisher"):
                        lines.append(f"  publisher = {{{s['publisher']}}},")
                    lines.append("}")
                    return "\n".join(lines)

                def _chicago(s: Dict[str, Any], idx: int) -> str:
                    authors_raw = s.get("authors")
                    if isinstance(authors_raw, list) and authors_raw:
                        if len(authors_raw) == 1:
                            authors = authors_raw[0]
                        elif len(authors_raw) == 2:
                            parts = authors_raw[0].rsplit(" ", 1)
                            last = parts[-1] if len(parts) > 1 else parts[0]
                            authors = f"{last}, {authors_raw[0]} and {authors_raw[1]}"
                        else:
                            parts = authors_raw[0].rsplit(" ", 1)
                            last = parts[-1] if len(parts) > 1 else parts[0]
                            authors = f"{last}, {authors_raw[0]} et al."
                    else:
                        authors = str(authors_raw) if authors_raw else "Unknown Author"

                    title = s.get("title", "Untitled")
                    journal = s.get("journal") or s.get("publisher")
                    year = s.get("year", "n.d.")
                    vol = s.get("volume")
                    issue = s.get("issue")
                    pages = s.get("pages")
                    doi = s.get("doi")
                    url = s.get("url")
                    accessed = s.get("accessed_date", today)

                    line = f'{authors}. "{title}."'
                    if journal:
                        line += f" *{journal}*"
                        if vol:
                            line += f" {vol}"
                            if issue:
                                line += f", no. {issue}"
                        line += f" ({year})"
                        if pages:
                            line += f": {pages}"
                        line += "."
                    else:
                        line += f" ({year})."
                    if doi:
                        line += f" https://doi.org/{doi}."
                    elif url:
                        line += f" Accessed {accessed}. {url}."
                    return line

                # Deduplicate by URL then title
                seen: Set[str] = set()
                deduped: List[Dict[str, Any]] = []
                src_list: List[Dict[str, Any]] = list(sources)
                for src in src_list:
                    key = str(src.get("url") or src.get("doi") or src.get("title") or "")
                    if key and key not in seen:
                        seen.add(key)
                        deduped.append(src)

                if bib_format == "json":
                    formatted = _json.dumps(deduped, indent=2, ensure_ascii=False)
                elif bib_format == "bibtex":
                    formatted = "\n\n".join(_bibtex(s, i) for i, s in enumerate(deduped, 1))
                elif bib_format == "chicago":
                    entries = [_chicago(s, i) for i, s in enumerate(deduped, 1)]
                    formatted = "\n\n".join(f"{i}. {e}" for i, e in enumerate(entries, 1))
                else:  # apa7 default
                    entries = [_apa7(s, i) for i, s in enumerate(deduped, 1)]
                    formatted = "\n\n".join(f"{i}. {e}" for i, e in enumerate(entries, 1))

                bib_payload: Dict[str, Any] = {
                    "topic": f"Bibliography ({len(deduped)} sources, {bib_format})",
                    "summary": (
                        f"{len(deduped)} unique sources formatted as {bib_format.upper()}. "
                        f"{len(src_list) - len(deduped)} duplicate(s) removed."
                    ),
                    "bibliography": formatted,
                    "source_count": len(deduped),
                    "duplicates_removed": len(src_list) - len(deduped),
                    "format": bib_format,
                    "status": "success",
                }
                return ToolResult(
                    content=formatted,
                    structured_content=bib_payload,
                )

            else:
                raise ToolError(f"Unknown operation: {operation}")

        except ToolError:
            raise
        except Exception as e:
            logger.error(f"Content operations failed: {e}")
            return format_research_analysis_markdown(
                {"topic": "Content Operations", "status": "error", "error": str(e)},
                "Content Operations",
            )

    @mcp.tool(
        annotations={
            "title": "Research Topic",
            "readOnlyHint": True,
            "openWorldHint": True,
            "destructiveHint": False,
            "idempotentHint": False,
        },
        timeout=180.0,
    )
    async def research_topic(
        topic: Annotated[
            str,
            Field(
                description=(
                    "Subject of the research. A topic or question in "
                    "`topic` mode (e.g. 'transformer attention'); an "
                    "entity name in `entity` mode (e.g. 'OpenAI', "
                    "'FastMCP', 'Linus Torvalds')."
                ),
                min_length=2,
                max_length=300,
            ),
        ],
        mode: Annotated[
            ResearchMode,
            Field(
                description=(
                    "topic  - search + fetch + extract findings from top sources.\n"
                    "entity - profile a named entity by fanning out across "
                    "web, news, GitHub, social, and academic sources in "
                    "parallel. Returns a unified multi-section report."
                ),
                default="topic",
            ),
        ] = "topic",
        sources: Annotated[
            Optional[List[str]],
            Field(
                description=(
                    "topic mode only: override the search step with these "
                    "specific URLs. Ignored in entity mode."
                ),
                default=None,
            ),
        ] = None,
        max_sources: Annotated[
            int,
            Field(
                description="Upper bound on sources per section.",
                ge=1,
                le=20,
                default=5,
            ),
        ] = 5,
        include_analysis: Annotated[
            bool,
            Field(
                description=(
                    "topic mode only: run key-findings extraction on " "retrieved content."
                ),
                default=True,
            ),
        ] = True,
        ctx: Optional[Context] = None,
    ) -> str:
        """
        End-to-end deterministic research workflow. One tool, two modes:

          topic  - open-ended search + fetch + extract
          entity - unified cross-source profile of a named entity

        Both modes auto-attach per-result quality scores and an aggregate
        confidence signal so callers can calibrate trust.
        """
        try:
            if mode == "entity":
                return await _run_entity_mode(topic, max_sources=max_sources, ctx=ctx)
            return await _run_topic_mode(
                topic,
                sources=sources,
                max_sources=max_sources,
                include_analysis=include_analysis,
            )
        except Exception as e:
            logger.error(f"Research topic failed: {e}")
            return format_research_analysis_markdown(
                {"topic": topic, "status": "error", "error": str(e)},
                "Topic Research",
            )


# ── Helpers used by research_topic modes ─────────────────────────────────────


async def _run_topic_mode(
    topic: str,
    *,
    sources: Optional[List[str]],
    max_sources: int,
    include_analysis: bool,
) -> str:
    """Topic research: search + fetch (concurrent) + extract key findings.

    Fetches run in parallel with a 15s per-source cap, so the total
    fetch phase takes ~15s regardless of how many sources are requested
    (vs the old serial loop which could exceed the tool timeout).
    """
    import math

    from rival_search_mcp.utils.scrapling_client import fetch_text

    logger.info("Starting comprehensive research on: %s", topic)

    if not sources:
        from rival_search_mcp.core.search.engines.duckduckgo.duckduckgo_engine import (
            DuckDuckGoSearchEngine,
        )

        engine = DuckDuckGoSearchEngine()
        results = await engine.search(query=topic, num_results=max_sources)
        sources = [r.url for r in results[:max_sources] if r.url]

    query_tokens = {t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", topic)}

    def _rank_sentence(s: str) -> float:
        if len(s) < 40 or len(s) > 600:
            return 0.0
        lower = s.lower()
        tok_hits = sum(1 for t in query_tokens if t in lower) if query_tokens else 0
        length_score = math.log10(max(1, len(s)) + 1) - 1.5
        return max(0.0, length_score) * (1 + 0.5 * tok_hits)

    async def _fetch_one(source_url: str) -> Optional[Dict[str, Any]]:
        try:
            clean_content = await asyncio.wait_for(fetch_text(source_url), timeout=15.0)
            if not clean_content:
                return None
            return {
                "url": source_url,
                "title": source_url,
                "content": clean_content,
                "content_length": len(clean_content),
            }
        except Exception as e:
            logger.warning("Failed to retrieve content from %s: %s", source_url, e)
            return None

    fetch_results = await asyncio.gather(*[_fetch_one(u) for u in sources])
    sources_researched: List[Dict[str, Any]] = [r for r in fetch_results if r is not None]

    key_findings: List[str] = []
    if include_analysis:
        for src in sources_researched:
            sentences = re.split(r"(?<=[.!?])\s+", src["content"])
            ranked = sorted(
                ((s.strip(), _rank_sentence(s)) for s in sentences),
                key=lambda pair: pair[1],
                reverse=True,
            )
            key_findings.extend(s for s, score in ranked[:3] if score > 0)

    scored = assess_results(sources_researched)
    confidence = summarize_quality(scored)

    if scored:
        summary = (
            f"Research on '{topic}': {len(scored)} sources, {len(key_findings)} key findings. "
            f"Confidence {confidence['confidence']} "
            f"(mean {confidence['mean_score']}/100, "
            f"{confidence['independent_domains']} independent domains)."
        )
    else:
        summary = f"Research on '{topic}': no sources retrieved."

    return format_research_analysis_markdown(
        {
            "topic": topic,
            "summary": summary,
            "key_findings": key_findings,
            "sources": scored,
            "confidence": confidence,
            "status": "success",
        },
        "Topic Research",
    )


async def _report(ctx: Optional[Context], progress: float, total: float, message: str) -> None:
    """Best-effort progress reporter; silent if no ctx is bound."""
    if ctx is None:
        return
    try:
        await ctx.report_progress(progress=progress, total=total, message=message)
    except Exception:
        pass


async def _run_entity_mode(
    entity: str,
    *,
    max_sources: int,
    ctx: Optional[Context] = None,
) -> str:
    """Unified cross-source entity profile: web + news + github + social
    + academic fanned out in parallel, per-result quality, aggregate
    confidence."""
    from rival_search_mcp.core.news.aggregator import NewsAggregator
    from rival_search_mcp.core.scientific.search.orchestrator import AcademicSearchOrchestrator
    from rival_search_mcp.core.social.bluesky import BlueskySearch
    from rival_search_mcp.core.social.hackernews import HackerNewsSearch
    from rival_search_mcp.core.social.reddit import RedditSearch
    from rival_search_mcp.core.social.stackoverflow import StackOverflowSearch
    from rival_search_mcp.tools.multi_search import MultiSearchOrchestrator

    logger.info("Profiling entity: %s", entity)

    tasks: Dict[str, Any] = {
        "web": MultiSearchOrchestrator().search_all_engines(
            query=entity,
            num_results=max_sources,
            extract_content=False,
            follow_links=False,
            max_depth=1,
        ),
        "news": NewsAggregator().search_news(
            query=entity, max_results=max_sources, time_range="month"
        ),
        "hn": HackerNewsSearch().search(query=entity, limit=max_sources),
        "reddit": RedditSearch().search(
            query=entity, subreddit="all", limit=max_sources, time_filter="month"
        ),
        "so": StackOverflowSearch().search(query=entity, site="stackoverflow", limit=max_sources),
        "bsky": BlueskySearch().search(query=entity, limit=max_sources),
        "academic": AcademicSearchOrchestrator().search_academic_papers(
            query=entity,
            sources=["openalex", "crossref", "arxiv"],
            limit=max_sources,
        ),
    }

    try:
        from rival_search_mcp.core.github_api.search import GitHubSearch

        tasks["github"] = GitHubSearch().search_repositories(query=entity, per_page=max_sources)
    except Exception as e:
        logger.debug("github fan-out skipped: %s", e)

    await _report(ctx, 10, 100, f"fanning out to {len(tasks)} sources")

    names = list(tasks.keys())
    outs = await asyncio.gather(*tasks.values(), return_exceptions=True)
    by_name = dict(zip(names, outs))

    await _report(ctx, 55, 100, "fan-out complete, normalizing results")

    sections: Dict[str, List[Dict[str, Any]]] = {
        "web": [],
        "news": [],
        "github": [],
        "social": [],
        "academic": [],
    }
    failures: Dict[str, str] = {}

    web = by_name.get("web")
    if isinstance(web, Exception):
        failures["web"] = str(web)
    elif isinstance(web, dict):
        for engine_data in (web.get("results") or {}).values():
            for r in (engine_data or {}).get("results", []):
                if isinstance(r, dict):
                    sections["web"].append(r)
                elif hasattr(r, "to_dict"):
                    sections["web"].append(r.to_dict())

    news = by_name.get("news")
    if isinstance(news, Exception):
        failures["news"] = str(news)
    elif isinstance(news, list):
        sections["news"] = list(news)

    github = by_name.get("github")
    if isinstance(github, Exception):
        failures["github"] = str(github)
    elif isinstance(github, list):
        for r in github:
            if "url" not in r and "html_url" in r:
                r["url"] = r["html_url"]
            sections["github"].append(r)

    for key in ("hn", "reddit", "so", "bsky"):
        data = by_name.get(key)
        if isinstance(data, Exception):
            failures[key] = str(data)
        elif isinstance(data, list):
            for item in data:
                if "text" in item and "title" not in item:
                    item["title"] = item["text"][:120]
                sections["social"].append(item)

    academic = by_name.get("academic")
    if isinstance(academic, Exception):
        failures["academic"] = str(academic)
    elif isinstance(academic, list):
        sections["academic"] = list(academic)

    await _report(ctx, 75, 100, "scoring results")

    for key in list(sections.keys()):
        sections[key] = assess_results(sections[key])[:max_sources]

    union = [it for items in sections.values() for it in items]
    union_annotated = assess_results(
        [{k: v for k, v in it.items() if k != "quality"} for it in union]
    )
    confidence = summarize_quality(union_annotated)

    await _report(ctx, 90, 100, "aggregating confidence")

    flat_findings: List[Dict[str, Any]] = []
    for section_name, items in sections.items():
        for it in items:
            enriched = dict(it)
            enriched.setdefault("section", section_name)
            flat_findings.append(enriched)
    await _report(ctx, 100, 100, "done")

    md = f"# 🗺️ Entity Profile: *{entity}*\n\n"
    badge = {"high": "🟢", "medium": "🟡", "low": "🔴", "none": "⚪"}.get(
        confidence["confidence"], "⚪"
    )
    md += (
        f"**{badge} Confidence:** {confidence['confidence']} · "
        f"mean quality {confidence['mean_score']}/100 · "
        f"{confidence['independent_domains']} independent sources across "
        f"{confidence['result_count']} results\n\n---\n\n"
    )

    section_titles = {
        "web": "🌐 Web Overview",
        "news": "📰 Recent News",
        "github": "🐙 Code & Community",
        "social": "💬 Community Sentiment",
        "academic": "🔬 Academic Footprint",
    }
    for key, title in section_titles.items():
        items = sections.get(key, [])
        if not items:
            continue
        md += f"## {title}\n\n"
        for i, it in enumerate(items[:5], 1):
            heading = it.get("title") or it.get("name") or it.get("text", "")[:80]
            md += f"### {i}. {heading}\n\n"
            q = it.get("quality") or {}
            if q:
                md += f"**Quality:** {q.get('score', 0)}/100 " f"({q.get('tier', '?')})"
                sig = q.get("signals") or {}
                if sig.get("corroboration"):
                    md += f" · corroborated by {sig['corroboration']} other sources"
                md += "\n\n"
            if it.get("description"):
                md += f"{it['description'][:300]}\n\n"
            url = it.get("url") or it.get("link")
            if url:
                md += f"[🔗 Source]({url})\n\n"
            md += "---\n\n"

    if failures:
        md += "## ⚠️ Source Notes\n\n"
        for src_name, err in failures.items():
            md += f"- **{src_name}**: {err}\n"
        md += "\n"

    return md
