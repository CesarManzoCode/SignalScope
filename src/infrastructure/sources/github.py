"""
GitHub API client module.

This module provides functionality to fetch trending repositories
from the GitHub REST API and structure them into RawItem data classes
for consistent handling.
"""

import httpx
import asyncio
import os
from typing import Optional, Any
from dataclasses import dataclass, field

from core.types.raw_item import RawItem


def transform_to_raw_items(repos: list[dict[str, Any]]) -> list[RawItem]:
    """
    Transform raw GitHub repositories into RawItem instances.

    This method maps GitHub REST API responses to the RawItem data class,
    extracting relevant fields and providing sensible defaults.

    Args:
        repos (list[dict[str, Any]]): Raw repository dictionaries from the GitHub API.

    Returns:
        list[RawItem]: A list of RawItem instances populated with repository data.
    """
    raw_items = []

    for repo in repos:
        # Extract full repository name as title (owner/repo)
        title = repo.get("full_name", "unknown/unknown")

        # Extract public URL of the repository
        url = repo.get("html_url", "")

        # Extract description as summary, fallback to empty string
        summary = repo.get("description") or ""

        # Include repository topics as additional tags
        topics: list[str] = repo.get("topics", [])
        tags = ["github", "repository"] + topics

        # Build metadata dictionary with additional GitHub fields
        metadata = {
            "repo_id": repo.get("id"),
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "open_issues": repo.get("open_issues_count", 0),
            "watchers": repo.get("watchers_count", 0),
            "language": repo.get("language"),
            "owner": repo.get("owner", {}).get("login", "unknown"),
            "owner_type": repo.get("owner", {}).get("type", "unknown"),
            "is_fork": repo.get("fork", False),
            "license": repo.get("license", {}).get("spdx_id") if repo.get("license") else None,
            "default_branch": repo.get("default_branch", "main"),
            "visibility": repo.get("visibility", "public"),
        }

        # GitHub already returns dates in ISO 8601 format — no conversion needed
        raw_item = RawItem(
            title=title,
            summary=summary,
            url=url,
            source="github",
            tags=tags,
            metadata=metadata,
            published_at=repo.get("created_at"),
        )

        raw_items.append(raw_item)

    return raw_items


@dataclass
class GitHubClient:
    """
    Client for interacting with the GitHub REST API v3.

    Attributes:
        base_url (str): The base URL for the GitHub API.
        timeout (float): Request timeout in seconds.
        max_repos (int): Maximum number of repositories to fetch.
        token (Optional[str]): Personal access token for authentication.
                               Without a token, rate limit is 60 req/hour.
                               With a token, rate limit increases to 5000 req/hour.
    """

    base_url: str = "https://api.github.com"
    timeout: float = 10.0
    max_repos: int = 30
    token: Optional[str] = field(default_factory=lambda: os.getenv("GITHUB_TOKEN"))

    def _build_headers(self) -> dict[str, str]:
        """
        Build the HTTP headers required for the GitHub API.

        Includes the Accept header for the stable API version and,
        if available, the Bearer authentication token.

        Returns:
            dict[str, str]: HTTP headers ready to use in each request.
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def fetch_trending_repo_names(self, limit: int) -> list[str]:
        """
        Fetch full names ('owner/repo') of trending repositories.

        Uses GitHub's search endpoint sorted by stars within the last month
        to approximate the concept of "trending" repositories.

        Args:
            limit (int): Number of repository names to retrieve.

        Returns:
            list[str]: A list of full repository names.

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        from datetime import datetime, timezone, timedelta

        # Date 30 days ago in YYYY-MM-DD format for the search query
        since = (datetime.now(tz=timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

        params = {
            "q": f"created:>{since}",
            "sort": "stars",
            "order": "desc",
            "per_page": min(limit, 100),  # GitHub allows a maximum of 100 results per page
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/search/repositories",
                headers=self._build_headers(),
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            return [repo["full_name"] for repo in items[:limit]]

    async def fetch_repo(
        self,
        client: httpx.AsyncClient,
        full_name: str,
    ) -> Optional[dict[str, Any]]:
        """
        Fetch the complete data of a repository by its full name.

        Args:
            client (httpx.AsyncClient): Shared HTTP client across tasks.
            full_name (str): Full repository name ('owner/repo').

        Returns:
            Optional[dict[str, Any]]: Repository data as a dictionary,
                                      or None if the request fails.
        """
        try:
            response = await client.get(
                f"{self.base_url}/repos/{full_name}",
                headers=self._build_headers(),
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as error:
            print(f"Failed to fetch repo {full_name}: {error}")
            return None

    async def fetch_repos_batch(self, full_names: list[str]) -> list[dict[str, Any]]:
        """
        Fetch multiple repositories concurrently.

        Args:
            full_names (list[str]): List of full repository names to fetch.

        Returns:
            list[dict[str, Any]]: A list of repository data dictionaries.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tasks = [self.fetch_repo(client, name) for name in full_names]
            results = await asyncio.gather(*tasks)
        return [repo for repo in results if repo is not None]

    async def fetch_and_transform(self, limit: Optional[int] = None) -> list[RawItem]:
        """
        Main method to fetch trending repositories and transform them into RawItem instances.

        This is the primary entry point for fetching GitHub repositories.
        It orchestrates fetching repository names, fetching individual repository
        data, and transforming them into the desired data structure.

        Args:
            limit (Optional[int]): Maximum number of repositories to fetch.
                                   Defaults to max_repos if not provided.

        Returns:
            list[RawItem]: A list of RawItem instances containing GitHub repository data.
        """
        fetch_limit = limit or self.max_repos
        repo_names = await self.fetch_trending_repo_names(fetch_limit)
        repos = await self.fetch_repos_batch(repo_names)
        raw_items = transform_to_raw_items(repos)
        return raw_items