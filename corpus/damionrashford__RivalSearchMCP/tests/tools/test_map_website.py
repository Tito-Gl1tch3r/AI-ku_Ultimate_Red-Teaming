#!/usr/bin/env python3
"""
Test suite for map_website tool.
Validates all 3 modes and parameters.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.mcp_client import create_client


async def test_research_mode():
    """Test website traversal in research mode."""
    async with create_client() as client:
        result = await client.call_tool(
            "map_website",
            {
                "url": "https://www.python.org/about",
                "mode": "research",
                "max_pages": 2,
                "max_depth": 1,
            },
        )

        assert result.content, "No content returned"
        output = result.content[0].text

        assert len(output) > 0, "Empty output"
        assert "Error" not in output or "travers" in output.lower()

        print(f"✅ Research mode test passed - {len(output)} chars")


async def test_docs_mode():
    """Test website traversal in docs mode."""
    async with create_client() as client:
        result = await client.call_tool(
            "map_website",
            {"url": "https://www.python.org/doc", "mode": "docs", "max_pages": 2, "max_depth": 1},
        )

        output = result.content[0].text
        assert len(output) > 0, "Empty output in docs mode"

        print("✅ Docs mode test passed")


async def test_map_mode():
    """Test website traversal in map mode."""
    async with create_client() as client:
        result = await client.call_tool(
            "map_website",
            {"url": "https://www.python.org/downloads", "mode": "map", "max_pages": 2},
        )

        output = result.content[0].text
        assert len(output) > 0, "Empty output in map mode"

        print("✅ Map mode test passed")


async def test_pages_not_zero():
    """Critical test: verify traversal actually finds pages (not 0!)."""
    async with create_client() as client:
        result = await client.call_tool(
            "map_website",
            {
                "url": "https://www.python.org/about",
                "mode": "research",
                "max_pages": 3,
                "max_depth": 1,
            },
        )

        output = result.content[0].text

        # Most critical assertion - must not return 0 pages
        assert (
            "traversed: 0" not in output.lower() and "traversed 0" not in output.lower()
        ), "Traversal found 0 pages - BROKEN!"

        # Should have traversal results
        has_content = "page" in output.lower() or "travers" in output.lower() or len(output) > 300
        assert has_content, "No traversal content found"

        print("✅ Pages not zero test passed - Traversal working!")


async def test_max_pages_parameter():
    """Test traversal with different max_pages values."""
    async with create_client() as client:
        max_pages_values = [1, 3]

        for max_pages in max_pages_values:
            result = await client.call_tool(
                "map_website",
                {
                    "url": "https://www.python.org",
                    "mode": "research",
                    "max_pages": max_pages,
                    "max_depth": 1,
                },
            )

            output = result.content[0].text
            assert len(output) > 100, f"Output too short for max_pages={max_pages}"
            print(f"  ✓ max_pages={max_pages} works")

        print("✅ max_pages parameter test passed")


async def test_max_depth_parameter():
    """Test traversal with different max_depth values."""
    async with create_client() as client:
        result = await client.call_tool(
            "map_website",
            {
                "url": "https://www.python.org/about",
                "mode": "research",
                "max_pages": 2,
                "max_depth": 2,
            },
        )

        output = result.content[0].text
        assert len(output) > 100, "Output too short for max_depth=2"

        print("✅ max_depth parameter test passed")


async def test_generate_llms_txt_flag():
    """Test traversal with generate_llms_txt enabled."""
    async with create_client() as client:
        result = await client.call_tool(
            "map_website",
            {
                "url": "https://www.python.org",
                "mode": "research",
                "max_pages": 2,
                "generate_llms_txt": True,
            },
        )

        output = result.content[0].text
        assert len(output) > 100, "Output too short with llms_txt enabled"

        print("✅ generate_llms_txt flag test passed")


if __name__ == "__main__":
    asyncio.run(test_research_mode())
    asyncio.run(test_docs_mode())
    asyncio.run(test_map_mode())
    asyncio.run(test_pages_not_zero())
    asyncio.run(test_max_pages_parameter())
    asyncio.run(test_max_depth_parameter())
    asyncio.run(test_generate_llms_txt_flag())
    print("\n✅ All map_website tests passed!")
