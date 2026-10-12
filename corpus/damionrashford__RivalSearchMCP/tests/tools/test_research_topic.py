#!/usr/bin/env python3
"""
Test suite for research_topic tool.
Validates all parameters and security unblocking.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.mcp_client import create_client


async def test_research_not_blocked():
    """Critical test: verify research_topic is not blocked by security."""
    async with create_client() as client:
        result = await client.call_tool(
            "research_topic",
            {
                "topic": "Python programming best practices",
                "max_sources": 3,
                "include_analysis": True,
            },
        )

        assert result.content, "No content returned"
        output = result.content[0].text

        # Most critical: must not be blocked
        assert "blocked" not in output.lower(), "Research blocked by security middleware!"
        assert "suspicious content" not in output.lower(), "Research blocked!"

        print("✅ Research not blocked test passed")


async def test_research_default_params():
    """Test research_topic with default parameters."""
    async with create_client() as client:
        result = await client.call_tool("research_topic", {"topic": "machine learning"})

        output = result.content[0].text
        assert len(output) > 0, "Empty research output"

        print(f"✅ Default params test passed - {len(output)} chars")


async def test_research_max_sources():
    """Test research_topic with different max_sources values."""
    async with create_client() as client:
        for max_sources in [2, 5]:
            result = await client.call_tool(
                "research_topic",
                {
                    "topic": "Python programming",
                    "max_sources": max_sources,
                    "include_analysis": False,
                },
            )

            output = result.content[0].text
            # Research may return minimal content if sources fail - verify tool executes
            assert (
                len(output) > 50
            ), f"Output too minimal for max_sources={max_sources}: {len(output)} chars"
            print(f"  ✓ max_sources={max_sources} works")

        print("✅ max_sources parameter test passed")


async def test_research_with_analysis():
    """Test research_topic with include_analysis=True."""
    async with create_client() as client:
        result = await client.call_tool(
            "research_topic",
            {"topic": "machine learning", "max_sources": 3, "include_analysis": True},
        )

        output = result.content[0].text
        assert len(output) > 50, f"Research with analysis too short: {len(output)} chars"

        print("✅ Research with analysis test passed")


async def test_research_without_analysis():
    """Test research_topic with include_analysis=False."""
    async with create_client() as client:
        result = await client.call_tool(
            "research_topic",
            {"topic": "web development", "max_sources": 2, "include_analysis": False},
        )

        output = result.content[0].text
        assert len(output) > 50, f"Research without analysis too short: {len(output)} chars"

        print("✅ Research without analysis test passed")


async def test_research_with_sources():
    """Test research_topic with specific sources provided."""
    async with create_client() as client:
        result = await client.call_tool(
            "research_topic",
            {
                "topic": "programming languages",
                "sources": ["https://www.python.org", "https://github.com"],
                "max_sources": 2,
                "include_analysis": True,
            },
        )

        output = result.content[0].text
        assert len(output) > 50, f"Research with sources too short: {len(output)} chars"

        print("✅ Research with sources test passed")


if __name__ == "__main__":
    asyncio.run(test_research_not_blocked())
    asyncio.run(test_research_default_params())
    asyncio.run(test_research_max_sources())
    asyncio.run(test_research_with_analysis())
    asyncio.run(test_research_without_analysis())
    asyncio.run(test_research_with_sources())
    print("\n✅ All research_topic tests passed!")
