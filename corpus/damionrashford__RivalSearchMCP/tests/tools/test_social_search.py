#!/usr/bin/env python3
"""Tests for social_search tool."""

import asyncio
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.mcp_client import create_client


@pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Pullpush.io is accessible from all IPs, but CI runners occasionally "
    "hit rate limits on external APIs. Covered by local test runs.",
)
async def test_reddit_search():
    """Test Reddit search via Pullpush.io."""
    async with create_client() as client:
        result = await client.call_tool(
            "social_search",
            {
                "query": "Python web frameworks",
                "platforms": ["reddit"],
                "max_results_per_platform": 5,
                "reddit_subreddit": "Python",
            },
        )

        output = result.content[0].text
        assert len(output) > 200, f"Reddit search output too short: {len(output)} chars"
        assert "reddit" in output.lower(), "No Reddit results found"
        print(f"✅ Reddit search test passed - {len(output)} chars")


async def test_hackernews_search():
    """Test HackerNews search via Algolia."""
    async with create_client() as client:
        result = await client.call_tool(
            "social_search",
            {"query": "TypeScript", "platforms": ["hackernews"], "max_results_per_platform": 5},
        )

        output = result.content[0].text
        assert len(output) > 200, f"HackerNews search output too short: {len(output)} chars"
        assert "hacker" in output.lower() or "news" in output.lower()
        print(f"✅ HackerNews search test passed - {len(output)} chars")


async def test_hackernews_long_query():
    """Long verbose queries should return results after normalization."""
    async with create_client() as client:
        result = await client.call_tool(
            "social_search",
            {
                "query": "smart home abandoned stopped using frustrated too complicated not worth it automation setup",
                "platforms": ["hackernews"],
                "max_results_per_platform": 5,
            },
        )

        output = result.content[0].text
        assert "Found 0 results" not in output, "Long HN query still returns 0 after normalization"
        print(f"✅ HackerNews long query test passed - {len(output)} chars")


async def test_bluesky_long_query():
    """Long verbose queries should return results after normalization."""
    async with create_client() as client:
        result = await client.call_tool(
            "social_search",
            {
                "query": "voice assistant wish it could help me clean guide me through tasks coaching not just commands",
                "platforms": ["bluesky"],
                "max_results_per_platform": 5,
            },
        )

        output = result.content[0].text
        assert (
            "Found 0 results" not in output
        ), "Long Bluesky query still returns 0 after normalization"
        print(f"✅ Bluesky long query test passed - {len(output)} chars")


async def test_devto_search():
    """Test Dev.to search."""
    async with create_client() as client:
        result = await client.call_tool(
            "social_search",
            {"query": "React", "platforms": ["devto"], "max_results_per_platform": 5},
        )

        output = result.content[0].text
        assert len(output) > 100, f"Dev.to search output too short: {len(output)} chars"
        print(f"✅ Dev.to search test passed - {len(output)} chars")


async def test_all_platforms():
    """All three previously-broken platforms return results for the same query."""
    async with create_client() as client:
        result = await client.call_tool(
            "social_search",
            {
                "query": "ADHD productivity tools focus",
                "platforms": ["reddit", "hackernews", "bluesky"],
                "max_results_per_platform": 3,
            },
        )

        output = result.content[0].text
        assert "Found 0 results" not in output, "Combined platform search returned nothing"
        assert len(output) > 300, f"Multi-platform search too short: {len(output)} chars"
        print(f"✅ All platforms test passed - {len(output)} chars")


async def test_time_filter():
    """Reddit time filter is passed through to Pullpush."""
    async with create_client() as client:
        result = await client.call_tool(
            "social_search",
            {
                "query": "Python",
                "platforms": ["reddit"],
                "time_filter": "week",
                "max_results_per_platform": 5,
            },
        )

        output = result.content[0].text
        assert len(output) > 100, "Time filter test output too short"
        print("✅ Time filter test passed")


if __name__ == "__main__":
    asyncio.run(test_reddit_search())
    asyncio.run(test_hackernews_search())
    asyncio.run(test_hackernews_long_query())
    asyncio.run(test_bluesky_long_query())
    asyncio.run(test_devto_search())
    asyncio.run(test_all_platforms())
    asyncio.run(test_time_filter())
    print("\n✅ All social_search tests passed!")
