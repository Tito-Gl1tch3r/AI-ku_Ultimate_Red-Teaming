#!/usr/bin/env python3
"""
Unified content extractors for RivalSearchMCP.
"""

from abc import ABC, abstractmethod
from typing import Any

from scrapling.parser import Selector

from rival_search_mcp.logging.logger import logger


class BaseContentExtractor(ABC):
    """Base class for content extractors."""

    def __init__(self):
        pass

    @abstractmethod
    def extract(self, content: str) -> Any:
        pass


class UnifiedContentExtractor(BaseContentExtractor):
    """Extracts readable text from HTML using Scrapling's Selector."""

    def extract(self, content: str) -> str:
        if not content:
            return ""
        try:
            sel = Selector(content=content)
            for css in (
                "main",
                '[role="main"]',
                ".main-content",
                ".content",
                ".post-content",
                ".article-content",
                "#content",
                "#main",
                ".entry-content",
                ".post-body",
                ".article-body",
                "body",
            ):
                el = sel.css_first(css)
                if el:
                    text = el.get_all_text(
                        separator=" ",
                        strip=True,
                        ignore_tags=("script", "style", "nav", "footer", "header", "aside"),
                    )
                    if len(text) > 100:
                        return text
            logger.warning("UnifiedContentExtractor: no content area found")
            return ""
        except Exception as e:
            logger.error("Content extraction failed: %s", e)
            return ""
