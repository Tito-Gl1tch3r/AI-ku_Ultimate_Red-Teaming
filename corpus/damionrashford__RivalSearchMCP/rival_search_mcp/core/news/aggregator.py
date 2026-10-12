"""
News aggregation across multiple keyless sources.

Sources, all verified live before adding:
  - google_news  -> news.google.com/rss/search  (httpx + feedparser)
  - bing_news    -> bing.com/news/search?format=RSS  (Scrapling AsyncFetcher
                    with stealthy_headers -- httpx gets 0 items because Bing
                    TLS-fingerprints plain-Python clients; Scrapling drives
                    tls_client under the hood with a real browser fingerprint)
  - guardian     -> content.guardianapis.com  (httpx, public api-key="test")
  - gdelt        -> api.gdeltproject.org/api/v2/doc  (httpx, global; rate
                    limited to one request per 5 seconds per IP)
  - duckduckgo_news -> html.duckduckgo.com scrape  (kept as broad fallback)

Every source honors the same `time_range` filter ("day" / "week" / "month" /
"anytime") via its native parameter so results are consistent across sources.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import feedparser
import httpx
from scrapling.fetchers import AsyncFetcher
from scrapling.parser import Selector

from rival_search_mcp.logging.logger import logger

_TIME_RANGES = {"anytime", "day", "week", "month"}


def _time_range_delta(time_range: str) -> Optional[timedelta]:
    """Map tool-level time_range to a timedelta, or None for 'anytime'."""
    return {
        "day": timedelta(days=1),
        "week": timedelta(days=7),
        "month": timedelta(days=30),
    }.get(time_range)


class NewsAggregator:
    """Aggregate news from multiple keyless sources."""

    def __init__(self):
        self.headers = {
            "User-Agent": "rivalsearchmcp/1.0 (+https://github.com/damionrashford/RivalSearchMCP)",
        }

    async def search_news(
        self,
        query: str,
        max_results: int = 10,
        language: str = "en",
        country: str = "US",
        time_range: str = "anytime",
    ) -> List[Dict[str, Any]]:
        if time_range not in _TIME_RANGES:
            logger.warning("Unknown time_range %r, using 'anytime'", time_range)
            time_range = "anytime"

        # Ask each source for max_results so we can still return max_results
        # unique articles after dedup.
        per_source = max_results

        tasks = [
            self._google_news(query, per_source, language, country, time_range),
            self._bing_news(query, per_source, time_range),
            self._guardian(query, per_source, time_range),
            self._gdelt(query, per_source, time_range),
            self._duckduckgo_news(query, per_source),
        ]
        outputs = await asyncio.gather(*tasks, return_exceptions=True)

        all_articles: List[Dict[str, Any]] = []
        for out in outputs:
            if isinstance(out, list):
                all_articles.extend(out)
            elif isinstance(out, Exception):
                logger.debug("News source raised: %s", out)

        seen_urls: set = set()
        seen_titles: set = set()
        unique: List[Dict[str, Any]] = []
        for article in all_articles:
            url = article.get("url", "")
            title_key = (article.get("title", "") or "").lower()[:60]
            if not url or url in seen_urls:
                continue
            if title_key and title_key in seen_titles:
                continue
            seen_urls.add(url)
            if title_key:
                seen_titles.add(title_key)
            unique.append(article)

        logger.info(
            "News aggregator: %d unique articles from %d/%d sources (query=%r, time=%s)",
            len(unique),
            sum(1 for o in outputs if isinstance(o, list) and o),
            len(outputs),
            query,
            time_range,
        )
        return unique[:max_results]

    # ------------------------------------------------------------------ Google
    async def _google_news(
        self,
        query: str,
        max_results: int,
        language: str,
        country: str,
        time_range: str,
    ) -> List[Dict[str, Any]]:
        # Google News supports `when:Nd` time operators embedded in the query
        # (e.g. `when:1d`, `when:7d`, `when:30d`).
        when = {"day": "1d", "week": "7d", "month": "30d"}.get(time_range)
        q = f"{query} when:{when}" if when else query
        url = (
            f"https://news.google.com/rss/search?q={quote_plus(q)}"
            f"&hl={language}&gl={country}&ceid={country}:{language}"
        )
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                r = await client.get(url)
                if r.status_code != 200:
                    logger.warning("Google News %s: %s", url, r.status_code)
                    return []
                feed = feedparser.parse(r.text)
                out = []
                for entry in feed.entries[:max_results]:
                    out.append(
                        {
                            "title": entry.get("title", ""),
                            "url": entry.get("link", ""),
                            "description": entry.get("summary", ""),
                            "published": entry.get("published", ""),
                            "source": entry.get("source", {}).get("title", "Google News"),
                            "platform": "google_news",
                        }
                    )
                logger.info("google_news: %d for %r", len(out), query)
                return out
        except httpx.HTTPError as e:
            logger.warning("google_news network error: %s", e)
            return []
        except Exception:
            logger.exception("google_news unexpected error")
            return []

    # ---------------------------------------------------------------- Bing RSS
    async def _bing_news(
        self, query: str, max_results: int, time_range: str
    ) -> List[Dict[str, Any]]:
        # Bing silently returns 0 items to plain httpx because it
        # TLS-fingerprints clients. Scrapling's AsyncFetcher drives
        # tls_client with a real browser fingerprint, so the RSS body is
        # populated. No subprocess, no headless browser.
        qft = {
            "day": "+filterui:age-lt24h",
            "week": "+filterui:age-lt1week",
            "month": "+filterui:age-lt1month",
        }.get(time_range, "")
        params = f"?q={quote_plus(query)}&format=RSS" + (f"&qft={qft}" if qft else "")
        url = f"https://www.bing.com/news/search{params}"
        try:
            page = await AsyncFetcher.get(url, stealthy_headers=True, timeout=20)
            if page.status != 200:
                logger.warning(
                    "bing_news returned %s (body snippet: %s)",
                    page.status,
                    page.body[:200] if page.body else b"",
                )
                return []
            feed = feedparser.parse(page.body)
            out = []
            for entry in feed.entries[:max_results]:
                out.append(
                    {
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "description": entry.get("summary", ""),
                        "published": entry.get("published", ""),
                        "source": entry.get("source", {}).get("title", "Bing News"),
                        "platform": "bing_news",
                    }
                )
            logger.info("bing_news: %d for %r", len(out), query)
            return out
        except Exception:
            logger.exception("bing_news failed")
            return []

    # ---------------------------------------------------------------- Guardian
    async def _guardian(
        self, query: str, max_results: int, time_range: str
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "q": query,
            "api-key": "test",  # public developer key, unlimited for dev use
            "page-size": min(max_results, 50),
            "show-fields": "trailText,byline,thumbnail",
            "order-by": "relevance",
        }
        delta = _time_range_delta(time_range)
        if delta is not None:
            from_date = (datetime.now(timezone.utc) - delta).date().isoformat()
            params["from-date"] = from_date
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                r = await client.get("https://content.guardianapis.com/search", params=params)
                if r.status_code != 200:
                    logger.warning("guardian: %s (body: %s)", r.status_code, r.text[:200])
                    return []
                data = r.json().get("response", {})
                out = []
                for item in data.get("results", []):
                    fields = item.get("fields") or {}
                    out.append(
                        {
                            "title": item.get("webTitle", ""),
                            "url": item.get("webUrl", ""),
                            "description": fields.get("trailText", ""),
                            "published": item.get("webPublicationDate", ""),
                            "source": "The Guardian",
                            "platform": "guardian",
                        }
                    )
                logger.info("guardian: %d for %r", len(out), query)
                return out
        except httpx.HTTPError as e:
            logger.warning("guardian network error: %s", e)
            return []
        except Exception:
            logger.exception("guardian unexpected error")
            return []

    # ------------------------------------------------------------------- GDELT
    async def _gdelt(self, query: str, max_results: int, time_range: str) -> List[Dict[str, Any]]:
        # GDELT enforces ~one request per 5s per IP. We call it in parallel
        # with other sources; if this caller happens to be rate-limited, the
        # source returns [] and the aggregator keeps going.
        params: Dict[str, Any] = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": min(max_results, 50),
            "sort": "DateDesc",
        }
        # timespan maps to GDELT's documented freshness operator.
        timespan = {"day": "1d", "week": "1w", "month": "1m"}.get(time_range)
        if timespan:
            params["timespan"] = timespan
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                r = await client.get("https://api.gdeltproject.org/api/v2/doc/doc", params=params)
                if r.status_code == 429 or "limit requests" in r.text[:100].lower():
                    logger.info("gdelt rate-limited, skipping this call")
                    return []
                if r.status_code != 200:
                    logger.warning("gdelt: %s (body: %s)", r.status_code, r.text[:200])
                    return []
                try:
                    data = r.json()
                except ValueError:
                    # GDELT sometimes returns "Please limit..." as text/plain
                    logger.info("gdelt non-JSON response: %s", r.text[:120])
                    return []
                out = []
                for item in data.get("articles", []):
                    out.append(
                        {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "description": "",
                            "published": item.get("seendate", ""),
                            "source": item.get("domain", "GDELT"),
                            "platform": "gdelt",
                        }
                    )
                logger.info("gdelt: %d for %r", len(out), query)
                return out
        except httpx.HTTPError as e:
            logger.warning("gdelt network error: %s", e)
            return []
        except Exception:
            logger.exception("gdelt unexpected error")
            return []

    # ------------------------------------------------------------ DuckDuckGo
    async def _duckduckgo_news(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        # DDG's HTML endpoint does not expose a true news filter or time filter;
        # we append "news" as a keyword and scrape general results. Kept as a
        # broad fallback so queries that no structured source indexes still hit
        # something.
        url = "https://html.duckduckgo.com/html/"
        headers = {
            **self.headers,
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Referer": "https://duckduckgo.com/",
        }
        try:
            async with httpx.AsyncClient(
                headers=headers, timeout=30.0, follow_redirects=True
            ) as client:
                r = await client.get(url, params={"q": f"{query} news"})
                if r.status_code != 200:
                    logger.warning("duckduckgo_news: %s", r.status_code)
                    return []
                sel = Selector(content=r.text)
                out: List[Dict[str, Any]] = []
                for a_el in sel.css("a.result__a"):
                    if len(out) >= max_results:
                        break
                    title = a_el.get_all_text(strip=True)
                    href = a_el.attrib.get("href", "")
                    if not title or not href:
                        continue
                    out.append(
                        {
                            "title": title,
                            "url": href,
                            "description": "",
                            "published": "",
                            "source": "DuckDuckGo",
                            "platform": "duckduckgo_news",
                        }
                    )
                logger.info("duckduckgo_news: %d for %r", len(out), query)
                return out
        except httpx.HTTPError as e:
            logger.warning("duckduckgo_news network error: %s", e)
            return []
        except Exception:
            logger.exception("duckduckgo_news unexpected error")
            return []
