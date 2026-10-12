"""
Utilities for formatting tool outputs as clean markdown.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


def format_social_media_markdown(query: str, results: Dict[str, Any]) -> str:
    """Format social search results as clean markdown."""
    output = f"# 💬 Social Search Results for: *{query}*\n\n"

    total_results = sum(r.get("count", 0) for r in results.values())
    platforms = [p for p, r in results.items() if r.get("count", 0) > 0]

    output += f"**Found {total_results} results** across {len(platforms)} platforms\n\n"
    output += "---\n\n"

    if total_results > 0:
        output += "💡 **Next Steps:**\n"
        output += "- Use `content_operations` to retrieve full content from discussion URLs\n"
        output += "- Use `find_conflicts` to surface disagreements between sources\n\n"
        output += "---\n\n"

    if "reddit" in results and results["reddit"].get("results"):
        output += "## Reddit Results\n\n"
        for i, post in enumerate(results["reddit"]["results"][:10], 1):
            output += f"### {i}. r/{post['subreddit']}: {post['title']}\n\n"
            output += f"**Score:** {post['score']} | **Comments:** {post['num_comments']} | **Author:** u/{post['author']}\n\n"
            if post.get("selftext"):
                output += f"{post['selftext'][:200]}...\n\n"
            output += f"[🔗 View on Reddit]({post['url']})\n\n"
            output += "---\n\n"

    if "hackernews" in results and results["hackernews"].get("results"):
        output += "## Hacker News Results\n\n"
        for i, story in enumerate(results["hackernews"]["results"][:10], 1):
            output += f"### {i}. {story['title']}\n\n"
            output += f"**Points:** {story['points']} | **Comments:** {story['num_comments']} | **By:** {story['author']}\n\n"
            if story.get("url"):
                output += f"[🔗 Article]({story['url']}) | "
            output += f"[💬 Discussion]({story['hn_url']})\n\n"
            output += "---\n\n"

    if "devto" in results and results["devto"].get("results"):
        output += "## Dev.to Results\n\n"
        for i, article in enumerate(results["devto"]["results"][:10], 1):
            output += f"### {i}. {article['title']}\n\n"
            output += f"**By:** {article['user']} | **Reactions:** {article['public_reactions_count']} | **Comments:** {article['comments_count']}\n\n"
            if article.get("description"):
                output += f"{article['description']}\n\n"
            output += f"**Tags:** {', '.join(article['tag_list'][:5])}\n\n"
            output += f"[🔗 Read Article]({article['url']})\n\n"
            output += "---\n\n"

    if "producthunt" in results and results["producthunt"].get("results"):
        output += "## Product Hunt Results\n\n"
        for i, product in enumerate(results["producthunt"]["results"][:10], 1):
            output += f"### {i}. {product['title']}\n\n"
            if product.get("tagline"):
                output += f"{product['tagline']}\n\n"
            if product.get("votes"):
                output += f"**Upvotes:** {product['votes']}\n\n"
            output += f"[🔗 View on Product Hunt]({product['url']})\n\n"
            output += "---\n\n"

    if "medium" in results and results["medium"].get("results"):
        output += "## Medium Results\n\n"
        for i, article in enumerate(results["medium"]["results"][:10], 1):
            output += f"### {i}. {article['title']}\n\n"
            if article.get("author"):
                output += f"**By:** {article['author']}\n\n"
            if article.get("summary"):
                output += f"{article['summary']}\n\n"
            output += f"[🔗 Read on Medium]({article['url']})\n\n"
            output += "---\n\n"

    if "stackoverflow" in results and results["stackoverflow"].get("results"):
        output += "## Stack Overflow Results\n\n"
        for i, q in enumerate(results["stackoverflow"]["results"][:10], 1):
            output += f"### {i}. {q['title']}\n\n"
            stats = (
                f"**Score:** {q.get('score', 0)} | "
                f"**Answers:** {q.get('answer_count', 0)} | "
                f"**Views:** {q.get('view_count', 0)}"
            )
            if q.get("accepted_answer_id"):
                stats += " | ✅ **Accepted answer**"
            output += stats + "\n\n"
            if q.get("author"):
                output += f"**By:** {q['author']}\n\n"
            if q.get("tags"):
                output += f"**Tags:** {', '.join(q['tags'][:5])}\n\n"
            output += f"[🔗 View Question]({q['url']})\n\n"
            output += "---\n\n"

    if "bluesky" in results and results["bluesky"].get("results"):
        output += "## Bluesky Results\n\n"
        for i, post in enumerate(results["bluesky"]["results"][:10], 1):
            display = post.get("author_display_name") or post.get("author_handle", "")
            handle = post.get("author_handle", "")
            output += f"### {i}. {display} (@{handle})\n\n"
            output += f"{post.get('text', '')}\n\n"
            output += (
                f"**♥ {post.get('like_count', 0)} · "
                f"🔁 {post.get('repost_count', 0)} · "
                f"💬 {post.get('reply_count', 0)}**\n\n"
            )
            if post.get("url"):
                output += f"[🔗 View Post]({post['url']})\n\n"
            output += "---\n\n"

    if "lobsters" in results and results["lobsters"].get("results"):
        output += "## Lobste.rs Results\n\n"
        for i, story in enumerate(results["lobsters"]["results"][:10], 1):
            output += f"### {i}. {story['title']}\n\n"
            output += (
                f"**Score:** {story.get('score', 0)} | "
                f"**Comments:** {story.get('comments_count', 0)}\n\n"
            )
            if story.get("tags"):
                output += f"**Tags:** {', '.join(story['tags'][:5])}\n\n"
            if story.get("byline"):
                output += f"*{story['byline']}*\n\n"
            if story.get("url"):
                output += f"[🔗 Link]({story['url']})"
                if story.get("comments_url"):
                    output += f" | [💬 Discussion]({story['comments_url']})"
                output += "\n\n"
            elif story.get("comments_url"):
                output += f"[💬 Discussion]({story['comments_url']})\n\n"
            output += "---\n\n"

    if "lemmy" in results and results["lemmy"].get("results"):
        output += "## Lemmy Results\n\n"
        for i, post in enumerate(results["lemmy"]["results"][:10], 1):
            community = post.get("community", "")
            output += f"### {i}. {post['title']}"
            if community:
                output += f" — *!{community}*"
            output += "\n\n"
            output += (
                f"**Score:** {post.get('score', 0)} | "
                f"**Comments:** {post.get('comments', 0)} | "
                f"**By:** {post.get('author', 'unknown')}\n\n"
            )
            if post.get("body"):
                output += f"{post['body'][:200]}\n\n"
            link = post.get("url") or post.get("ap_id", "")
            if link:
                output += f"[🔗 View Post]({link})\n\n"
            output += "---\n\n"

    output += f"*Search completed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    return output


def format_news_markdown(
    query: str,
    articles: List[Dict[str, Any]],
    time_range: str,
    confidence: Optional[Dict[str, Any]] = None,
) -> str:
    """Format news aggregation results as clean markdown.

    `confidence` is the aggregate summary from
    ``src.core.quality.summarize_quality``. When present, a
    trust-signal header is rendered; per-article `quality` blocks are
    folded into each item's metadata.
    """
    output = f"# 📰 News Search Results for: *{query}*\n\n"
    output += f"**Found {len(articles)} news articles**\n\n"
    if time_range != "anytime":
        output += f"**Time Range:** {time_range}\n\n"

    if confidence:
        conf = confidence.get("confidence", "unknown")
        badge = {"high": "🟢", "medium": "🟡", "low": "🔴", "none": "⚪"}.get(conf, "⚪")
        output += (
            f"**{badge} Confidence:** {conf} "
            f"(mean score {confidence.get('mean_score', 0)}/100, "
            f"{confidence.get('independent_domains', 0)} independent sources)\n\n"
        )

    output += "---\n\n"

    if len(articles) > 0:
        output += "💡 **Next Steps:**\n"
        output += "- Use `content_operations` to retrieve full article content\n"
        output += "- Use `document_analysis` if articles link to PDFs\n"
        output += "- Use `score_sources` to rate the returned URLs\n\n"
        output += "---\n\n"

    for i, article in enumerate(articles, 1):
        output += f"## {i}. {article.get('title', 'Untitled')}\n\n"

        # Quality chip for this article
        q = article.get("quality") or {}
        if q:
            output += f"**Quality:** {q.get('score', 0)}/100 ({q.get('tier', '?')})"
            sig = q.get("signals", {}) or {}
            corroboration = sig.get("corroboration")
            if corroboration:
                output += f" · corroborated by {corroboration} other source(s)"
            output += "\n\n"

        if article.get("source"):
            output += f"**Source:** {article['source']}"
        if article.get("published"):
            output += f" | **Published:** {article['published']}"
        output += "\n\n"

        if article.get("description"):
            output += f"{article['description']}\n\n"

        output += f"[🔗 Read Article]({article.get('url', '#')})\n\n"
        output += "---\n\n"

    output += f"*News search completed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    return output


def format_github_markdown(query: str, repositories: List[Dict[str, Any]]) -> str:
    """Format GitHub repository search results as clean markdown."""
    output = f"# 🐙 GitHub Repository Search: *{query}*\n\n"
    output += f"**Found {len(repositories)} repositories**\n\n"
    output += "---\n\n"

    if len(repositories) > 0:
        output += "💡 **Next Steps:**\n"
        output += "- Use `content_operations` to retrieve README files from repo URLs\n"
        output += "- Use `map_website` to explore repository documentation\n"
        output += "- Use `entity_research` for a unified cross-source profile\n\n"
        output += "---\n\n"

    for i, repo in enumerate(repositories, 1):
        output += f"## {i}. {repo.get('name', 'Unknown')}\n\n"

        if repo.get("description"):
            output += f"{repo['description']}\n\n"

        # Stats
        output += f"**⭐ Stars:** {repo.get('stars', 0)} | "
        output += f"**🔀 Forks:** {repo.get('forks', 0)} | "
        output += f"**Language:** {repo.get('language', 'N/A')} | "
        output += f"**Issues:** {repo.get('open_issues', 0)}\n\n"

        if repo.get("topics"):
            output += f"**Topics:** {', '.join(repo['topics'][:5])}\n\n"

        output += f"**Updated:** {repo.get('updated_at', 'Unknown')}\n\n"

        if repo.get("readme"):
            output += f"**README Preview:**\n```\n{repo['readme'][:300]}...\n```\n\n"

        output += f"[🔗 View on GitHub]({repo.get('url', '#')})\n\n"
        output += "---\n\n"

    output += f"*Search completed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    return output


def format_academic_search_markdown(results: Dict[str, Any]) -> str:
    """Format academic search results as clean markdown."""
    if results.get("status") != "success":
        return f"❌ **Error:** {results.get('error', 'Unknown error occurred')}"

    query = results.get("query", "")
    papers = results.get("results", [])
    metadata = results.get("metadata", {})

    output = f"# 🔬 Academic Search Results for: *{query}*\n\n"
    output += (
        f"**Found {len(papers)} papers** from {', '.join(metadata.get('sources_searched', []))}\n\n"
    )
    output += "---\n\n"

    if len(papers) > 0:
        output += "💡 **Next Steps:**\n"
        output += "- Use `document_analysis` to extract text from PDF links\n"
        output += "- Use `content_operations` to retrieve paper pages\n"
        output += "- Use `document_analysis` on PDF links for full text\n\n"
        output += "---\n\n"

    # Papers
    for i, paper in enumerate(papers, 1):
        output += f"## {i}. {paper.get('title', 'Untitled')}\n\n"

        # Authors
        authors = paper.get("authors", [])
        if authors:
            # Handle both string and dict formats
            author_names = []
            for author in authors:
                if isinstance(author, dict):
                    author_names.append(author.get("name", ""))
                else:
                    author_names.append(str(author))

            author_names = [name for name in author_names if name]  # Filter empty names

            if author_names:
                if len(author_names) <= 3:
                    author_str = ", ".join(author_names)
                else:
                    author_str = ", ".join(author_names[:3]) + " et al."
                output += f"**Authors:** {author_str}\n\n"

        # Basic info
        info_parts = []
        if paper.get("year"):
            info_parts.append(f"**Year:** {paper.get('year')}")
        if paper.get("venue"):
            info_parts.append(f"**Venue:** {paper.get('venue')}")
        if paper.get("citation_count"):
            info_parts.append(f"**Citations:** {paper.get('citation_count')}")

        if info_parts:
            output += " | ".join(info_parts) + "\n\n"

        # Abstract (truncated if too long)
        abstract = paper.get("abstract", "")
        if abstract:
            if len(abstract) > 500:
                abstract = abstract[:500] + "..."
            output += f"**Abstract:** {abstract}\n\n"

        # Links
        links = []
        if paper.get("url"):
            links.append(f"[📄 Paper]({paper.get('url')})")
        if paper.get("pdf_url"):
            links.append(f"[📕 PDF]({paper.get('pdf_url')})")

        if links:
            output += " | ".join(links) + "\n\n"

        # Citations if available
        citations = paper.get("citations", {})
        if citations:
            output += "**Citations:**\n\n"
            if citations.get("bibtex"):
                output += f"```\n{citations['bibtex']}\n```\n\n"
            if citations.get("apa"):
                output += f"*{citations['apa']}*\n\n"

        output += "---\n\n"

    output += f"*Search completed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"

    return output.strip()


def format_dataset_discovery_markdown(results: Dict[str, Any]) -> str:
    """Format dataset discovery results as clean markdown."""
    if results.get("status") != "success":
        return f"❌ **Error:** {results.get('error', 'Unknown error occurred')}"

    query = results.get("query", "")
    datasets = results.get("datasets", [])
    metadata = results.get("metadata", {})

    output = f"# 📊 Dataset Discovery Results for: *{query}*\n\n"
    output += f"**Found {len(datasets)} datasets** from {', '.join(metadata.get('sources_searched', []))}\n\n"
    output += "---\n\n"

    # Datasets
    for i, dataset in enumerate(datasets, 1):
        output += f"## {i}. {dataset.get('title', 'Untitled Dataset')}\n\n"

        # Owner/Source
        owner = dataset.get("owner", "")
        source = dataset.get("source", "")
        if owner:
            output += f"**Owner:** {owner} ({source})\n\n"

        # Description
        description = dataset.get("description", "")
        if description:
            if len(description) > 300:
                description = description[:300] + "..."
            output += f"**Description:** {description}\n\n"

        # Basic info
        info_parts = []
        if dataset.get("file_formats"):
            formats = [fmt for fmt in dataset.get("file_formats", []) if fmt]
            if formats:
                info_parts.append(f"**Formats:** {', '.join(formats[:3])}")
        if dataset.get("size"):
            info_parts.append(f"**Size:** {dataset.get('size')}")
        if dataset.get("license"):
            info_parts.append(f"**License:** {dataset.get('license')}")

        if info_parts:
            output += " | ".join(info_parts) + "\n\n"

        # Stats
        stats_parts = []
        if dataset.get("download_count") is not None:
            stats_parts.append(f"📥 {dataset.get('download_count')} downloads")
        if dataset.get("upvote_count") is not None:
            stats_parts.append(f"👍 {dataset.get('upvote_count')} upvotes")

        if stats_parts:
            output += " | ".join(stats_parts) + "\n\n"

        # Links
        links = []
        if dataset.get("url"):
            links.append(f"[🔗 View Dataset]({dataset.get('url')})")
        if dataset.get("download_url"):
            links.append(f"[⬇️ Download]({dataset.get('download_url')})")

        if links:
            output += " | ".join(links) + "\n\n"

        # Tags
        tags = dataset.get("tags", [])
        if tags:
            tag_str = " ".join(f"`{tag}`" for tag in tags[:5])
            output += f"**Tags:** {tag_str}\n\n"

        # Metadata if available
        dataset_metadata = dataset.get("metadata", {})
        if dataset_metadata and dataset_metadata.get("columns"):
            columns = dataset_metadata.get("columns", [])
            if columns:
                output += f"**Columns:** {', '.join(columns[:10])}{'...' if len(columns) > 10 else ''}\n\n"

        output += "---\n\n"

    output += f"*Search completed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"

    return output.strip()


def format_multi_search_markdown(results: Dict[str, Any]) -> str:
    """Format multi-search results as clean markdown."""
    # Check for error status
    if results.get("status") == "error" or "error" in results:
        return f"❌ **Error:** {results.get('error', 'Unknown error occurred')}"

    query = results.get("query", results.get("summary", {}).get("query", ""))
    results_data = results.get("results", {})

    output = f"# 🔍 Search Results for: *{query}*\n\n"

    total_results = 0
    successful_engines = 0
    for engine, engine_data in results_data.items():
        if engine_data.get("status") == "success":
            count = engine_data.get("count", 0)
            total_results += count
            successful_engines += 1
            output += f"**{engine.title()}:** {count} results\n"

    output += f"\n**Total Results:** {total_results} from {successful_engines} engines\n\n"
    output += "---\n\n"

    # Results by engine
    for engine, engine_data in results_data.items():
        if engine_data.get("status") == "success" and engine_data.get("results"):
            output += f"## {engine.title()} Results\n\n"

            for i, result in enumerate(engine_data["results"], 1):
                title = result.get("title", "Untitled")
                url = result.get("url", "")
                description = result.get("description", "")

                output += f"### {i}. {title}\n\n"

                if description:
                    # Truncate description if too long
                    if len(description) > 200:
                        description = description[:200] + "..."
                    output += f"{description}\n\n"

                if url:
                    output += f"[🔗 Visit Page]({url})\n\n"

                output += "---\n\n"

    output += f"*Search completed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"

    return output.strip()


def format_research_analysis_markdown(results: Dict[str, Any], tool_name: str = "Research") -> str:
    """Format research/analysis results as clean markdown."""
    if results.get("status") != "success":
        return f"❌ **Error:** {results.get('error', 'Unknown error occurred')}"

    topic = results.get("topic", "")
    output = f"# 📋 {tool_name} Analysis: *{topic}*\n\n"

    # Summary
    summary = results.get("summary", "")
    if summary:
        output += f"## Summary\n\n{summary}\n\n"

    # Key findings
    findings = results.get("key_findings", [])
    if findings:
        output += "## Key Findings\n\n"
        for i, finding in enumerate(findings, 1):
            output += f"{i}. {finding}\n"
        output += "\n"

    # Sources
    sources = results.get("sources", [])
    if sources:
        output += "## Sources\n\n"
        for i, source in enumerate(sources, 1):
            title = source.get("title", "Untitled")
            url = source.get("url", "")
            if url:
                output += f"{i}. [{title}]({url})\n"
            else:
                output += f"{i}. {title}\n"
        output += "\n"

    # AI Insights (special handling)
    ai_insights = results.get("ai_insights")
    if ai_insights:
        output += "## 🤖 AI Insights\n\n"
        output += f"{ai_insights}\n\n"

    # Additional sections
    for section_name, section_data in results.items():
        if section_name not in [
            "status",
            "topic",
            "summary",
            "key_findings",
            "sources",
            "timestamp",
            "ai_insights",  # Already handled above
        ]:
            if isinstance(section_data, list) and section_data:
                output += f"## {section_name.replace('_', ' ').title()}\n\n"
                for item in section_data:
                    output += f"- {item}\n"
                output += "\n"
            elif isinstance(section_data, str) and section_data:
                output += f"## {section_name.replace('_', ' ').title()}\n\n{section_data}\n\n"

    output += f"*Analysis completed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"

    return output.strip()


def format_traversal_markdown(results: Dict[str, Any]) -> str:
    """Format website traversal results as clean markdown."""
    if not results.get("success"):
        return f"❌ **Error:** {results.get('summary', 'Unknown error occurred')}"

    url = results.get("source", "")
    mode = results.get("mode", "research")
    pages = results.get("pages", [])
    total_pages = results.get("total_pages", 0)

    output = f"# 🌐 Website Traversal Results: {url}\n\n"
    output += f"**Mode:** {mode.title()} | **Pages Traversed:** {total_pages}\n\n"
    output += f"{results.get('summary', '')}\n\n"
    output += "---\n\n"

    # Pages
    for i, page in enumerate(pages, 1):
        title = page.get("title", "Untitled Page")
        page_url = page.get("url", "")
        depth = page.get("depth", 0)
        content = page.get("content", "")

        output += f"## {i}. {title}\n\n"
        output += f"**URL:** [{page_url}]({page_url})\n"
        output += f"**Depth:** {depth}\n\n"

        # Content preview (first 500 chars)
        if content:
            preview = content[:500] + "..." if len(content) > 500 else content
            output += f"**Content Preview:**\n\n{preview}\n\n"

        output += "---\n\n"

    # LLMs.txt if available
    if results.get("llms_txt"):
        output += "## 📄 LLMs.txt Generated\n\n"
        output += "A structured documentation file has been generated for LLM consumption.\n\n"

    output += f"*Traversal completed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"

    return output.strip()


def format_trends_markdown(results: Dict[str, Any]) -> str:
    """Format Google Trends results as clean markdown."""
    if not results.get("success"):
        return f"❌ **Error:** {results.get('error', 'Unknown error occurred')}"

    output = "# 📈 Google Trends Analysis\n\n"

    # Handle different result types
    if "data" in results:
        data = results["data"]
        if isinstance(data, list) and data:
            output += "## Trends Data\n\n"
            output += "| Date | Value |\n"
            output += "|------|-------|\n"
            for row in data[:20]:  # Limit to 20 rows for readability
                if isinstance(row, dict):
                    date = row.get("date", row.get("time", ""))
                    value = row.get(
                        "value", row.get(list(row.keys())[1] if len(row) > 1 else "value", "")
                    )
                    output += f"| {date} | {value} |\n"
            if len(data) > 20:
                output += f"\n*Showing first 20 of {len(data)} entries*\n"
            output += "\n"

    if "related_queries" in results:
        output += "## Related Queries\n\n"
        queries = results["related_queries"]
        if queries:
            for query_type, query_data in queries.items():
                if query_data:
                    output += f"### {query_type.replace('_', ' ').title()}\n\n"
                    if isinstance(query_data, list):
                        for item in query_data[:10]:
                            output += f"- {item}\n"
                    output += "\n"

    if "related_topics" in results:
        output += "## Related Topics\n\n"
        topics = results["related_topics"]
        if topics:
            for topic_type, topic_data in topics.items():
                if topic_data:
                    output += f"### {topic_type.replace('_', ' ').title()}\n\n"
                    if isinstance(topic_data, list):
                        for item in topic_data[:10]:
                            output += f"- {item}\n"
                    output += "\n"

    if "interest_by_region" in results:
        output += "## Interest by Region\n\n"
        regions = results["interest_by_region"]
        if isinstance(regions, list) and regions:
            output += "| Region | Interest |\n"
            output += "|--------|----------|\n"
            for row in regions[:15]:
                if isinstance(row, dict):
                    region = row.get("geoName", row.get("region", ""))
                    interest = row.get("value", row.get("interest", ""))
                    output += f"| {region} | {interest} |\n"
            output += "\n"

    if "trending_searches" in results:
        output += "## Trending Searches\n\n"
        trending = results["trending_searches"]
        if trending:
            for item in trending[:10]:
                output += f"- {item}\n"
            output += "\n"

    if "interest_over_time" in results:
        output += "## Interest Over Time\n\n"
        time_data = results["interest_over_time"]
        if isinstance(time_data, list) and time_data:
            output += "| Date | Interest |\n"
            output += "|------|----------|\n"
            for row in time_data[:20]:
                if isinstance(row, dict):
                    date = row.get("date", "")
                    interest = row.get(list(row.keys())[1] if len(row) > 1 else "interest", "")
                    output += f"| {date} | {interest} |\n"
            if len(time_data) > 20:
                output += f"\n*Showing first 20 of {len(time_data)} entries*\n"
            output += "\n"

    output += f"*Analysis completed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"

    return output.strip()


def format_document_markdown(result: Dict[str, Any], summary_length: int = 500) -> str:
    """Format document analysis results as clean markdown."""
    doc_type = result.get("document_type", "document").upper()
    output = f"# 📄 Document Analysis ({doc_type})\n\n"

    if result.get("status") == "error":
        return output + f"❌ **Error:** {result.get('error', 'Unknown error')}"

    output += f"**URL:** {result.get('url', 'Unknown')}\n\n"
    output += f"**Status:** {result.get('status', 'Unknown').title()}\n\n"
    output += "---\n\n"

    # Document info
    output += "## Document Information\n\n"
    output += f"- **Document Type:** {result.get('document_type', 'Unknown').upper()}\n"

    if result.get("total_pages"):
        output += f"- **Total Pages:** {result.get('total_pages', 0)}\n"
        output += f"- **Pages Extracted:** {result.get('pages_extracted', 0)}\n"

    if result.get("paragraphs"):
        output += f"- **Paragraphs:** {result.get('paragraphs', 0)}\n"

    if result.get("lines"):
        output += f"- **Lines:** {result.get('lines', 0)}\n"

    if result.get("image_size"):
        output += f"- **Image Size:** {result.get('image_size')}\n"

    if result.get("ocr_used"):
        output += "- **OCR Used:** Yes ✨\n"

    output += f"- **Text Length:** {result.get('text_length', 0)} characters\n\n"

    # Metadata
    if result.get("metadata"):
        meta = result["metadata"]
        output += "## Metadata\n\n"
        if meta.get("title"):
            output += f"- **Title:** {meta['title']}\n"
        if meta.get("author"):
            output += f"- **Author:** {meta['author']}\n"
        if meta.get("subject"):
            output += f"- **Subject:** {meta['subject']}\n"
        output += "\n"

    # Text preview
    if result.get("text"):
        text = result["text"]
        preview = text[:summary_length] if len(text) > summary_length else text
        output += "## Text Content Preview\n\n"
        output += f"```\n{preview}\n```\n\n"
        if len(text) > summary_length:
            output += f"*Showing first {summary_length} characters of {len(text)} total*\n\n"

    output += "---\n\n"
    output += f"*Analysis completed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    return output
