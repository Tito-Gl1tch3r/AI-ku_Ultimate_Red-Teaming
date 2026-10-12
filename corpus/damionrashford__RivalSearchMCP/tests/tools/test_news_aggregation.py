#!/usr/bin/env python3
"""
Test suite for news_aggregation tool.
Validates news search from multiple sources.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.mcp_client import create_client


async def test_news_basic():
    """Test basic news aggregation."""
    async with create_client() as client:
        result = await client.call_tool(
            "news_aggregation", {"query": "Python programming", "max_results": 5}
        )

        output = result.content[0].text
        # News may have limited results depending on availability
        assert len(output) > 100, f"News output too short: {len(output)} chars"
        assert "news" in output.lower() or "article" in output.lower(), "No news content found"

        print(f"✅ Basic news test passed - {len(output)} chars")


async def test_news_language():
    """Test news with language parameter."""
    async with create_client() as client:
        result = await client.call_tool(
            "news_aggregation",
            {"query": "artificial intelligence", "max_results": 5, "language": "en"},
        )

        output = result.content[0].text
        assert len(output) > 100, "Language filter output too short"

        print("✅ Language parameter test passed")


async def test_news_max_results():
    """Test news with different max_results values."""
    async with create_client() as client:
        for max_results in [3, 10]:
            result = await client.call_tool(
                "news_aggregation", {"query": "technology", "max_results": max_results}
            )

            output = result.content[0].text
            assert len(output) > 100, f"Output too short for max_results={max_results}"
            print(f"  ✓ max_results={max_results} works")

        print("✅ max_results parameter test passed")


async def test_news_quality():
    """Test that news returns quality results."""
    async with create_client() as client:
        result = await client.call_tool(
            "news_aggregation", {"query": "TypeScript 2026", "max_results": 5}
        )

        output = result.content[0].text
        assert len(output) > 100, f"News quality output: {len(output)} chars"
        # Should have URLs or article markers
        has_content = (
            "http" in output.lower() or "article" in output.lower() or "news" in output.lower()
        )
        assert has_content, "No article content found"

        print(f"✅ News quality test passed - {len(output)} chars")


if __name__ == "__main__":
    asyncio.run(test_news_basic())
    asyncio.run(test_news_language())
    asyncio.run(test_news_max_results())
    asyncio.run(test_news_quality())
    print("\n✅ All news_aggregation tests passed!")
