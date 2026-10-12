"""
Lobste.rs search.

Lobste.rs exposes JSON feeds for the hot/newest lists (`/hottest.json`,
`/newest.json`) but its `/search.json` endpoint rejects the search
parameters with HTTP 400 (Rails' form-param validator). The real
search is only available via the HTML page at `/search`. We parse
that page for the story list.

When `query` is empty we fall back to `/hottest.json` as a pure JSON
discovery feed.
"""

from typing import Any, Dict, List
from urllib.parse import quote_plus

import httpx
from scrapling.parser import Selector

from rival_search_mcp.logging.logger import logger


def _parse_story(li) -> Dict[str, Any]:
    link = li.css_first(".link a.u-url")
    title = link.get_all_text(strip=True) if link else ""
    url = link.attrib.get("href", "") if link else ""
    upvoter = li.css_first(".voters a.upvoter")
    score = 0
    if upvoter:
        try:
            score = int(upvoter.get_all_text(strip=True))
        except ValueError:
            score = 0
    tags = [t.get_all_text(strip=True) for t in li.css(".tags a.tag")]
    byline = li.css_first(".byline")
    byline_text = byline.get_all_text(" ", strip=True) if byline else ""
    comments_link = li.css_first(".comments_label a")
    comments_url = ""
    comments_count = 0
    if comments_link:
        href = comments_link.attrib.get("href", "")
        comments_url = href if href.startswith("http") else f"https://lobste.rs{href}"
        label = comments_link.get_all_text(strip=True)
        for tok in label.split():
            if tok.isdigit():
                comments_count = int(tok)
                break
    return {
        "title": title,
        "url": url,
        "score": score,
        "tags": tags,
        "byline": byline_text,
        "comments_url": comments_url,
        "comments_count": comments_count,
        "source": "lobsters",
    }


class LobstersSearch:
    """Search Lobste.rs stories (HTML scrape) with a hot-feed fallback."""

    def __init__(self):
        self.base_url = "https://lobste.rs"
        self.headers = {
            "User-Agent": (
                "rivalsearchmcp/1.0 (+https://github.com/damionrashford/RivalSearchMCP)"
            ),
        }

    async def search(
        self, query: str, limit: int = 10, what: str = "stories"
    ) -> List[Dict[str, Any]]:
        """
        Search Lobste.rs stories.

        Args:
            query: Search query (empty returns hottest stories)
            limit: Max results
            what: "stories" or "comments" (stories only by default)
        """
        try:
            async with httpx.AsyncClient(
                headers=self.headers, timeout=30.0, follow_redirects=True
            ) as client:
                if query:
                    url = (
                        f"{self.base_url}/search?q={quote_plus(query)}"
                        f"&what={quote_plus(what)}&order=relevance"
                    )
                    r = await client.get(url)
                    if r.status_code != 200:
                        logger.warning(
                            "Lobste.rs /search returned %s for %r (body: %s)",
                            r.status_code,
                            query,
                            r.text[:200],
                        )
                        return []
                    sel = Selector(content=r.text)
                    stories = sel.css("ol.stories li.story")[:limit]
                    results = [_parse_story(s) for s in stories]
                    logger.info("Found %d Lobste.rs stories for %r", len(results), query)
                    return results

                # Empty query → hottest feed (JSON)
                r = await client.get(f"{self.base_url}/hottest.json")
                if r.status_code != 200:
                    logger.warning(
                        "Lobste.rs /hottest.json returned %s (body: %s)",
                        r.status_code,
                        r.text[:200],
                    )
                    return []
                data = r.json()
                results = []
                for story in data[:limit]:
                    submitter = story.get("submitter_user") or {}
                    if isinstance(submitter, dict):
                        author = submitter.get("username", "")
                    else:
                        author = str(submitter)
                    results.append(
                        {
                            "title": story.get("title", ""),
                            "url": story.get("url") or story.get("short_id_url", ""),
                            "score": story.get("score", 0),
                            "tags": story.get("tags", []),
                            "byline": author,
                            "comments_url": story.get("comments_url", ""),
                            "comments_count": story.get("comment_count", 0),
                            "source": "lobsters",
                        }
                    )
                logger.info("Found %d Lobste.rs hot stories", len(results))
                return results

        except httpx.HTTPError as e:
            logger.warning("Lobste.rs search failed (network): %s", e)
            return []
        except Exception:
            logger.exception("Lobste.rs search failed (unexpected)")
            return []
