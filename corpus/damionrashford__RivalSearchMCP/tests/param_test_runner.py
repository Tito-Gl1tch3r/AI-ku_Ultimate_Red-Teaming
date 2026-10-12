#!/usr/bin/env python3
"""
Systematic parameter testing for RivalSearchMCP tools.
Run: python tests/param_test_runner.py [tool_name]
Run all: python tests/param_test_runner.py all
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.mcp_client import create_client

# Test URL - example.com is reliable (http avoids SSL cert issues on some macOS setups)
TEST_URL = "http://example.com"
TEST_PDF = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"


async def test_web_search_params(client):
    """Test web_search parameters."""
    tests = [
        ("baseline", {"query": "Python", "num_results": 3}),
        ("num_results=1", {"query": "Python", "num_results": 1}),
        ("num_results=20", {"query": "Python", "num_results": 20}),
        ("extract_content=false", {"query": "Python", "extract_content": False}),
        ("follow_links=false", {"query": "Python", "follow_links": False}),
        ("max_depth=1", {"query": "Python", "max_depth": 1}),
        ("use_fallback=false", {"query": "Python", "use_fallback": False}),
    ]
    return await _run_tests(client, "web_search", tests)


async def test_social_search_params(client):
    """Test social_search parameters."""
    tests = [
        ("baseline", {"query": "Python", "max_results_per_platform": 3}),
        (
            "platforms=reddit",
            {"query": "Python", "platforms": ["reddit"], "max_results_per_platform": 2},
        ),
        (
            "platforms=hackernews",
            {"query": "Python", "platforms": ["hackernews"], "max_results_per_platform": 2},
        ),
        ("max_results override", {"query": "Python", "max_results": 5}),
        (
            "time_filter=week",
            {
                "query": "Python",
                "platforms": ["reddit"],
                "time_filter": "week",
                "max_results_per_platform": 2,
            },
        ),
    ]
    return await _run_tests(client, "social_search", tests)


async def test_news_aggregation_params(client):
    """Test news_aggregation parameters."""
    tests = [
        ("baseline", {"query": "Python", "max_results": 5}),
        ("max_results=3", {"query": "AI", "max_results": 3}),
        ("language=es", {"query": "Python", "language": "es", "max_results": 3}),
        ("time_range=day", {"query": "Python", "time_range": "day", "max_results": 3}),
    ]
    return await _run_tests(client, "news_aggregation", tests)


async def test_github_search_params(client):
    """Test github_search parameters."""
    tests = [
        ("baseline", {"query": "fastmcp", "max_results": 3}),
        ("language=Python", {"query": "web framework", "language": "Python", "max_results": 3}),
        ("sort=forks", {"query": "fastmcp", "sort": "forks", "max_results": 3}),
        ("sort=updated", {"query": "fastmcp", "sort": "updated", "max_results": 3}),
    ]
    return await _run_tests(client, "github_search", tests)


async def test_content_operations_params(client):
    """Test content_operations parameters."""
    tests = [
        (
            "retrieve markdown",
            {"operation": "retrieve", "url": TEST_URL, "extraction_method": "markdown"},
        ),
        ("retrieve text", {"operation": "retrieve", "url": TEST_URL, "extraction_method": "text"}),
        ("extract links", {"operation": "extract", "url": TEST_URL, "max_links": 5}),
        (
            "analyze general",
            {
                "operation": "analyze",
                "content": "FastMCP is a Python framework for MCP servers.",
                "analysis_type": "general",
            },
        ),
        (
            "analyze sentiment",
            {"operation": "analyze", "content": "This is great!", "analysis_type": "sentiment"},
        ),
    ]
    return await _run_tests(client, "content_operations", tests)


async def test_map_website_params(client):
    """Test map_website parameters."""
    tests = [
        ("baseline research", {"url": TEST_URL, "mode": "research", "max_pages": 2}),
        ("mode=docs", {"url": TEST_URL, "mode": "docs", "max_pages": 2}),
        ("mode=map", {"url": TEST_URL, "mode": "map", "max_pages": 2}),
        ("max_depth=1", {"url": TEST_URL, "max_depth": 1, "max_pages": 2}),
    ]
    return await _run_tests(client, "map_website", tests)


async def test_research_topic_params(client):
    """Test research_topic parameters."""
    tests = [
        ("baseline", {"topic": "Python programming", "max_sources": 3}),
        (
            "include_analysis=false",
            {"topic": "Python", "include_analysis": False, "max_sources": 3},
        ),
    ]
    return await _run_tests(client, "research_topic", tests)


async def test_scientific_research_params(client):
    """Test scientific_research parameters."""
    tests = [
        (
            "academic_search",
            {"operation": "academic_search", "query": "machine learning", "max_results": 3},
        ),
        (
            "dataset_discovery",
            {"operation": "dataset_discovery", "query": "machine learning", "max_results": 3},
        ),
        (
            "academic sources=arxiv",
            {
                "operation": "academic_search",
                "query": "neural networks",
                "sources": ["arxiv"],
                "max_results": 2,
            },
        ),
    ]
    return await _run_tests(client, "scientific_research", tests)


async def test_document_analysis_params(client):
    """Test document_analysis parameters."""
    tests = [
        ("baseline PDF", {"url": TEST_PDF}),
        ("max_pages=1", {"url": TEST_PDF, "max_pages": 1}),
        ("extract_metadata=false", {"url": TEST_PDF, "extract_metadata": False}),
    ]
    return await _run_tests(client, "document_analysis", tests)


async def test_research_agent_params(client):
    """Test research_agent parameters."""
    tests = [
        ("baseline", {"topic": "Python programming", "max_sources": 5, "research_depth": "basic"}),
        (
            "research_depth=comprehensive",
            {"topic": "web development", "research_depth": "comprehensive", "max_sources": 5},
        ),
        ("include_trends=false", {"topic": "Python", "include_trends": False, "max_sources": 5}),
    ]
    return await _run_tests(client, "research_agent", tests)


async def _run_tests(client, tool_name: str, tests: list) -> list:
    """Run tests for a tool and return results."""
    results = []
    for name, args in tests:
        try:
            r = await client.call_tool(tool_name, args)
            ok = bool(r.content)
            ln = len(r.content[0].text) if r.content else 0
            if r.content:
                text = r.content[0].text
                if "❌" in text or ("Error" in text and "Invalid" in text):
                    ok = False
                # Retrieve should return actual content, not just error message
                if tool_name == "content_operations" and "retrieve" in name:
                    if ln == 0 or "Failed to retrieve" in text:
                        ok = False
            results.append((name, ok, ln))
        except Exception as e:
            results.append((name, False, str(e)))

    return results


TOOL_TESTS = {
    "web_search": test_web_search_params,
    "social_search": test_social_search_params,
    "news_aggregation": test_news_aggregation_params,
    "github_search": test_github_search_params,
    "content_operations": test_content_operations_params,
    "map_website": test_map_website_params,
    "research_topic": test_research_topic_params,
    "scientific_research": test_scientific_research_params,
    "document_analysis": test_document_analysis_params,
    "research_agent": test_research_agent_params,
}


async def main():
    tool = sys.argv[1] if len(sys.argv) > 1 else "web_search"
    print(f"\n=== Parameter Tests: {tool} ===\n")

    if tool == "all":
        tools = list(TOOL_TESTS.keys())
    elif tool in TOOL_TESTS:
        tools = [tool]
    else:
        print(f"Unknown tool: {tool}")
        print(f"Available: {', '.join(TOOL_TESTS.keys())}, all")
        return 1

    all_results = {}
    async with create_client() as client:
        for t in tools:
            results = await TOOL_TESTS[t](client)
            all_results[t] = results

    # Report
    log_path = (
        Path(__file__).parent.parent
        / "logs"
        / f"param_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    log_path.parent.mkdir(exist_ok=True)

    total_pass = 0
    total_fail = 0
    for tool_name, results in all_results.items():
        passed = sum(1 for _, ok, _ in results if ok)
        failed = [(n, ok, ln) for n, ok, ln in results if not ok]
        total_pass += passed
        total_fail += len(failed)

        print(f"\n{tool_name}:")
        for name, ok, ln in results:
            status = "✅" if ok else "❌"
            val = ln if isinstance(ln, int) else str(ln)[:50]
            print(f"  {status} {name}: {val}")
        print(f"  {passed}/{len(results)} passed")
        if failed:
            print(f"  FAILED: {[n for n, _, _ in failed]}")

    report = {
        "timestamp": datetime.now().isoformat(),
        "tools": list(all_results.keys()),
        "total_passed": total_pass,
        "total_failed": total_fail,
        "results": {
            k: [{"name": n, "ok": ok, "len": ln} for n, ok, ln in v] for k, v in all_results.items()
        },
    }
    log_path.write_text(json.dumps(report, indent=2))
    print(f"\nLog: {log_path}")
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
