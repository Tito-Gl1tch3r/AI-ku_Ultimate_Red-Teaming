#!/usr/bin/env python3
"""
Specialized traversal functionality for RivalSearchMCP.
Different types of traversal for research, documentation, and website mapping.
"""

from typing import Any, Dict, List

from .core import WebsiteTraverser


async def research_topic(url: str, max_pages: int = 20, max_depth: int = 2) -> List[Dict[str, Any]]:
    """
    Research a topic by traversing relevant websites.

    Args:
        url: URL to start traversal from (changed from topic to match actual usage)
        max_pages: Maximum pages to visit
        max_depth: Maximum traversal depth

    Returns:
        List of page data
    """
    # Use the provided URL directly for traversal
    traverser = WebsiteTraverser()
    return await traverser.traverse_website(url, max_depth, max_pages)


async def explore_documentation(
    docs_url: str, max_pages: int = 30, max_depth: int = 3
) -> List[Dict[str, Any]]:
    """
    Explore documentation websites.

    Args:
        docs_url: Documentation base URL
        max_pages: Maximum pages to visit
        max_depth: Maximum traversal depth

    Returns:
        List of page data
    """
    traverser = WebsiteTraverser()
    return await traverser.traverse_website(docs_url, max_depth, max_pages)


async def map_website_structure(
    website_url: str, max_pages: int = 50, max_depth: int = 3
) -> List[Dict[str, Any]]:
    """
    Map the structure of a website.

    Args:
        website_url: Website URL to map
        max_pages: Maximum pages to visit
        max_depth: Maximum traversal depth

    Returns:
        List of page data with structure information
    """
    traverser = WebsiteTraverser()
    pages = await traverser.traverse_website(website_url, max_depth, max_pages)

    # Add structure information
    for page in pages:
        page["structure_info"] = {
            "depth": page["url"].count("/") - 2,  # Rough depth calculation
            "is_homepage": page["url"].rstrip("/") == website_url.rstrip("/"),
            "has_navigation": "nav" in page["html"].lower() or "menu" in page["html"].lower(),
        }

    return pages
