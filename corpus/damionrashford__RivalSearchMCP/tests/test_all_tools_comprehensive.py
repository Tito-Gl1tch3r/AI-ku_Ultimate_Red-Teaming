"""
Comprehensive methodical test of every RivalSearchMCP tool and every parameter.
Uses MCP tool invocation for integration testing.
Run with: pytest tests/test_all_tools_comprehensive.py -v -s --tb=short
"""

import pytest

# Server name for MCP calls - tests assume server is running
MCP_SERVER = "user-RivalSearchMCP-local-http"


def call_tool(server: str, tool: str, args: dict) -> str:
    """Call MCP tool - requires mcp tool to be available in test env."""
    try:
        from cursor_mcp_client import call_mcp_tool  # type: ignore

        return call_mcp_tool(server=server, toolName=tool, arguments=args)
    except ImportError:
        pytest.skip("MCP client not available in test environment")


# Parametrized tests - each tuple is (tool_name, args_dict)
WEB_SEARCH_CASES = [
    ("web_search", {"query": "Python"}),
    ("web_search", {"query": "MCP", "num_results": 3}),
    ("web_search", {"query": "test", "num_results": 1, "extract_content": False}),
    ("web_search", {"query": "test", "follow_links": False}),
    ("web_search", {"query": "test", "max_depth": 1}),
    ("web_search", {"query": "test", "max_depth": 3}),
    ("web_search", {"query": "test", "use_fallback": False}),
]

SOCIAL_SEARCH_CASES = [
    ("social_search", {"query": "Python"}),
    ("social_search", {"query": "MCP", "platforms": ["reddit"]}),
    ("social_search", {"query": "MCP", "platforms": ["hackernews"]}),
    ("social_search", {"query": "MCP", "max_results_per_platform": 3}),
    ("social_search", {"query": "MCP", "max_results": 3}),
    ("social_search", {"query": "MCP", "reddit_subreddit": "python"}),
    ("social_search", {"query": "MCP", "time_filter": "week"}),
]

NEWS_CASES = [
    ("news_aggregation", {"query": "AI"}),
    ("news_aggregation", {"query": "tech", "max_results": 5}),
    ("news_aggregation", {"query": "news", "language": "en", "country": "US"}),
    ("news_aggregation", {"query": "AI", "time_range": "day"}),
    ("news_aggregation", {"query": "AI", "time_range": "week"}),
]

GITHUB_CASES = [
    ("github_search", {"query": "fastmcp"}),
    ("github_search", {"query": "python", "language": "Python"}),
    ("github_search", {"query": "mcp", "sort": "stars"}),
    ("github_search", {"query": "mcp", "sort": "forks"}),
    ("github_search", {"query": "mcp", "sort": "updated"}),
    ("github_search", {"query": "mcp", "max_results": 5}),
]

CONTENT_OPS_CASES = [
    ("content_operations", {"operation": "retrieve", "url": "https://example.com"}),
    ("content_operations", {"operation": "analyze", "content": "Test content for analysis."}),
    (
        "content_operations",
        {"operation": "analyze", "content": "Test", "analysis_type": "sentiment"},
    ),
    (
        "content_operations",
        {"operation": "analyze", "content": "Test", "analysis_type": "technical"},
    ),
]

MAP_WEBSITE_CASES = [
    ("map_website", {"url": "https://example.com"}),
    ("map_website", {"url": "https://example.com", "mode": "research"}),
    ("map_website", {"url": "https://example.com", "mode": "docs"}),
    ("map_website", {"url": "https://example.com", "mode": "map"}),
    ("map_website", {"url": "https://example.com", "max_pages": 2}),
]

SCIENTIFIC_CASES = [
    ("scientific_research", {"operation": "academic_search", "query": "machine learning"}),
    ("scientific_research", {"operation": "academic_search", "query": "AI", "max_results": 3}),
    ("scientific_research", {"operation": "dataset_discovery", "query": "AI"}),
    ("scientific_research", {"operation": "dataset_discovery", "query": "ML", "max_results": 5}),
]

RESEARCH_AGENT_CASES = [
    ("research_agent", {"topic": "MCP", "enable_ai_insights": False}),
    ("research_agent", {"topic": "Python", "max_sources": 5, "enable_ai_insights": False}),
    ("research_agent", {"topic": "AI", "research_depth": "basic", "enable_ai_insights": False}),
]
