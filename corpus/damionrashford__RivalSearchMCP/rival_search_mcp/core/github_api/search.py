"""
GitHub repository search using public API.
No authentication required for public repository searches.
"""

import base64
import time
from typing import Any, Dict, List, Optional

import httpx

from rival_search_mcp.logging.logger import logger


class GitHubSearch:
    """Search GitHub repositories without authentication.

    Rate Limits (no auth):
    - 60 requests per hour per IP
    - Resets every hour
    """

    def __init__(self):
        self.api_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "RivalSearchMCP/1.0",
        }
        self.request_count = 0
        self.last_reset_time = time.time()

    def _check_rate_limit(self):
        """Check and enforce GitHub API rate limits (60 req/hour for no auth)."""
        current_time = time.time()

        # Reset counter every hour
        if current_time - self.last_reset_time > 3600:
            self.request_count = 0
            self.last_reset_time = current_time
            logger.info("GitHub API rate limit counter reset")

        # Check if we're approaching the limit
        if self.request_count >= 55:  # Leave buffer of 5
            logger.warning(
                f"GitHub API rate limit approaching: {self.request_count}/60 requests used"
            )
            if self.request_count >= 60:
                remaining_time = 3600 - (current_time - self.last_reset_time)
                logger.error(
                    f"GitHub API rate limit exceeded. Resets in {remaining_time/60:.1f} minutes"
                )
                raise Exception(
                    f"GitHub API rate limit exceeded. Try again in {remaining_time/60:.1f} minutes"
                )

        self.request_count += 1

    async def search_repositories(
        self,
        query: str,
        language: Optional[str] = None,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search GitHub repositories with rate limiting.

        Rate Limit: 60 requests/hour without authentication.

        Args:
            query: Search query
            language: Filter by programming language
            sort: Sort by (stars, forks, updated)
            order: Order (desc, asc)
            per_page: Results per page (max 100)

        Returns:
            List of repository dictionaries
        """
        try:
            # Check rate limit before making request
            self._check_rate_limit()
            # Build search query
            search_query = query
            if language:
                search_query += f" language:{language}"

            url = f"{self.api_url}/search/repositories"
            params = {
                "q": search_query,
                "sort": sort,
                "order": order,
                "per_page": min(per_page, 30),  # Limit to 30 for no-auth
            }

            async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                repositories = []

                for repo in data.get("items", []):
                    repositories.append(
                        {
                            "name": repo.get("full_name", ""),
                            "description": repo.get("description", ""),
                            "url": repo.get("html_url", ""),
                            "stars": repo.get("stargazers_count", 0),
                            "forks": repo.get("forks_count", 0),
                            "language": repo.get("language", ""),
                            "open_issues": repo.get("open_issues_count", 0),
                            "created_at": repo.get("created_at", ""),
                            "updated_at": repo.get("updated_at", ""),
                            "topics": repo.get("topics", []),
                            "owner": repo.get("owner", {}).get("login", ""),
                            "source": "github",
                        }
                    )

                logger.info(f"Found {len(repositories)} GitHub repositories for: {query}")
                return repositories

        except Exception as e:
            logger.error(f"GitHub search failed: {e}")
            return []

    async def get_readme(self, owner: str, repo: str) -> Optional[str]:
        """
        Get repository README content with rate limiting.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            README content as string or None
        """
        try:
            # Check rate limit
            self._check_rate_limit()
            url = f"{self.api_url}/repos/{owner}/{repo}/readme"

            async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                data = response.json()
                content = base64.b64decode(data.get("content", "")).decode("utf-8")

                logger.info(f"Retrieved README for {owner}/{repo}")
                return content

        except Exception as e:
            logger.error(f"Failed to get README for {owner}/{repo}: {e}")
            return None
