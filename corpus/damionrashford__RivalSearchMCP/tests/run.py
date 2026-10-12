#!/usr/bin/env python3
"""
Individual test runner for RivalSearchMCP tools.
Run one tool test at a time for focused debugging.

Usage:
    # Test individual tools
    uv run python tests/run.py multi_search
    uv run python tests/run.py trends_core
    uv run python tests/run.py trends_export
    uv run python tests/run.py content_operations
    uv run python tests/run.py traverse_website
    uv run python tests/run.py research_topic
    uv run python tests/run.py scientific_research
    uv run python tests/run.py research_workflow

    # Or run the test file directly
    uv run python tests/tools/test_multi_search.py
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Run a specific tool test."""

    available_tools = {
        "multi_search": "tests/tools/test_multi_search.py",
        "trends_core": "tests/tools/test_trends_core.py",
        "trends_export": "tests/tools/test_trends_export.py",
        "content_operations": "tests/tools/test_content_operations.py",
        "traverse_website": "tests/tools/test_traverse_website.py",
        "research_topic": "tests/tools/test_research_topic.py",
        "scientific_research": "tests/tools/test_scientific_research.py",
        "research_workflow": "tests/tools/test_research_workflow.py",
    }

    if len(sys.argv) < 2:
        print("\n❌ Error: Please specify which tool to test\n")
        print("Available tools:")
        for i, tool in enumerate(available_tools.keys(), 1):
            print(f"  {i}. {tool}")
        print("\nUsage:")
        print("  uv run python tests/run.py <tool_name>")
        print("\nExample:")
        print("  uv run python tests/run.py multi_search")
        print("\nOr run test file directly:")
        print("  uv run python tests/tools/test_multi_search.py")
        sys.exit(1)

    tool_name = sys.argv[1]

    if tool_name not in available_tools:
        print(f"\n❌ Error: Unknown tool '{tool_name}'\n")
        print("Available tools:")
        for tool in available_tools.keys():
            print(f"  - {tool}")
        sys.exit(1)

    test_file = available_tools[tool_name]

    print(f"\n{'='*80}")
    print(f"  Testing Tool: {tool_name}")
    print(f"  Test File: {test_file}")
    print(f"{'='*80}\n")

    # Run the test file
    result = subprocess.run(["python", test_file], cwd=Path(__file__).parent.parent)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
