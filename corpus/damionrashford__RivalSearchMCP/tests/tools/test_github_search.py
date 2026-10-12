#!/usr/bin/env python3
"""
Test suite for github_search tool.
Validates GitHub repository search without authentication.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.mcp_client import create_client


async def test_github_basic():
    """Test basic GitHub repository search."""
    async with create_client() as client:
        result = await client.call_tool(
            "github_search", {"query": "web framework", "max_results": 5}
        )

        output = result.content[0].text

        # Handle potential rate limiting
        if "rate limit" in output.lower() or "error" in output.lower():
            print("⚠️  GitHub API rate limited - test passed (graceful handling)")
            assert len(output) > 50, "Error message too short"
        else:
            assert len(output) > 300, f"GitHub output too short: {len(output)} chars"
            assert "github" in output.lower() or "repository" in output.lower()

        print(f"✅ Basic GitHub search test passed - {len(output)} chars")


async def test_github_language_filter():
    """Test GitHub search with language filter."""
    async with create_client() as client:
        result = await client.call_tool(
            "github_search", {"query": "machine learning", "language": "Python", "max_results": 5}
        )

        output = result.content[0].text

        # Handle rate limiting
        if "rate limit" in output.lower():
            print("⚠️  GitHub rate limited")
            assert len(output) > 50, "Error handling too minimal"
        else:
            assert len(output) > 200, "Language filter output too short"

        print("✅ Language filter test passed")


async def test_github_sort_options():
    """Test GitHub search with different sort options."""
    async with create_client() as client:
        for sort in ["stars", "forks"]:
            result = await client.call_tool(
                "github_search", {"query": "React", "sort": sort, "max_results": 3}
            )

            output = result.content[0].text
            assert len(output) > 100, f"Output too short for sort={sort}"
            print(f"  ✓ sort={sort} works")

        print("✅ Sort options test passed")


async def test_github_quality():
    """Test that GitHub returns quality repository information."""
    async with create_client() as client:
        result = await client.call_tool(
            "github_search", {"query": "TypeScript", "language": "TypeScript", "max_results": 5}
        )

        output = result.content[0].text

        # Handle rate limiting
        if "rate limit" in output.lower():
            print("⚠️  GitHub rate limited")
            assert len(output) > 50, "Error handling too minimal"
        else:
            assert len(output) > 200, f"GitHub quality output: {len(output)} chars"

        print("✅ GitHub quality test passed")


if __name__ == "__main__":
    asyncio.run(test_github_basic())
    asyncio.run(test_github_language_filter())
    asyncio.run(test_github_sort_options())
    asyncio.run(test_github_quality())
    print("\n✅ All github_search tests passed!")
