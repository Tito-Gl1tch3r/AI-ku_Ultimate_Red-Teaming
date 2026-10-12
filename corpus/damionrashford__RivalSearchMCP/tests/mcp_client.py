#!/usr/bin/env python3
"""
FastMCP Client for RivalSearchMCP - Professional test client implementation.
This file provides a reusable client for interacting with the RivalSearchMCP server.

Usage:
    from tests.mcp_client import create_client

    async with create_client() as client:
        result = await client.call_tool("multi_search", {"query": "test"})
        print(result.content[0].text)
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import Client
from fastmcp.client import PythonStdioTransport


def create_client(server_path: Optional[str] = None) -> Client:
    """
    Create a FastMCP client for RivalSearchMCP server.

    Args:
        server_path: Path to server.py (default: auto-detect)

    Returns:
        Configured FastMCP Client instance

    Example:
        async with create_client() as client:
            tools = await client.list_tools()
            print(f"Available tools: {len(tools.tools)}")
    """
    if server_path is None:
        # Auto-detect server.py in parent directory
        server_path = str(Path(__file__).parent.parent / "server.py")

    # Create transport for local Python server
    transport = PythonStdioTransport(server_path)

    # Create and return client
    return Client(transport)


async def demo():
    """Demo usage of the FastMCP client."""
    print("\n🚀 RivalSearchMCP FastMCP Client Demo")
    print("=" * 80 + "\n")

    async with create_client() as client:
        # 1. List all available tools
        print("📋 Listing available tools...")
        tools_result = await client.list_tools()
        tools = tools_result.tools
        print(f"✅ Found {len(tools)} tools:\n")
        for i, tool in enumerate(tools, 1):
            print(f"  {i}. {tool.name}")
            if tool.description:
                desc = tool.description.split("\n")[0][:80]
                print(f"     {desc}{'...' if len(desc) >= 80 else ''}")

        print("\n" + "=" * 80)

        # 2. Test a simple tool
        print("\n🔬 Testing content_operations tool...")
        result = await client.call_tool(
            "content_operations",
            {
                "operation": "retrieve",
                "url": "https://example.com",
                "extraction_method": "markdown",
            },
        )

        output = result.content[0].text if result.content else "No output"
        print(f"✅ Result length: {len(output)} characters")
        print(f"   Preview: {output[:200]}...\n")

        print("=" * 80)
        print("\n✅ FastMCP Client is working correctly!")
        print("   Use create_client() in your tests to interact with the server.\n")


if __name__ == "__main__":
    # Run demo
    asyncio.run(demo())
