"""
Dev.to API client module.

This module provides functionality to fetch articles from the Dev.to forem API
and structure them into RawItem data classes for consistent handling.
"""

import httpx
from typing import Optional, Any
from dataclasses import dataclass, field
import os

from core.types.raw_item import RawItem


def transform_to_raw_items(articles: list[dict[str, Any]]) -> list[RawItem]:
    """
    Transform raw Dev.to articles into RawItem instances.

    This method maps Dev.to API responses to the RawItem data class,
    extracting relevant fields and providing sensible defaults.

    Args:
        articles (list[dict[str, Any]]): Raw article dictionaries from the Dev.to API.

    Returns:
        list[RawItem]: A list of RawItem instances populated with article data.
    """
    raw_items = []

    for article in articles:
        # Extract article title with fallback
        title = article.get("title", "Untitled")

        # Extract canonical URL, fallback to Dev.to URL
        url = article.get("canonical_url") or article.get("url", "")

        # Extract description as summary, fallback to empty string
        summary = article.get("description") or ""

        # Include article tags as additional tags
        article_tags: list[str] = article.get("tag_list", [])
        tags = ["dev_to", "article"] + article_tags

        # Extract author details from nested user object
        user: dict[str, Any] = article.get("user", {})

        # Build metadata dictionary with additional Dev.to fields
        metadata = {
            "article_id": article.get("id"),
            "reactions": article.get("public_reactions_count", 0),
            "comments": article.get("comments_count", 0),
            "reading_time": article.get("reading_time_minutes", 0),
            "author": user.get("name", "Anonymous"),
            "author_username": user.get("username", ""),
            "cover_image": article.get("cover_image"),
            "social_image": article.get("social_image"),
        }

        raw_item = RawItem(
            title=title,
            summary=summary,
            url=url,
            source="dev_to",
            tags=tags,
            metadata=metadata,
            published_at=article.get("published_at"),  # Already in ISO 8601 format
        )

        raw_items.append(raw_item)

    return raw_items


@dataclass
class DevToClient:
    """
    Client for interacting with the Dev.to forem REST API.

    Attributes:
        base_url (str): The base URL for the Dev.to API.
        timeout (float): Request timeout in seconds.
        max_articles (int): Maximum number of articles to fetch.
        api_key (Optional[str]): Dev.to API key for authenticated requests.
                                 Without a key, only public endpoints are available.
    """

    base_url: str = "https://dev.to/api"
    timeout: float = 10.0
    max_articles: int = 30
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("DEVTO_API_KEY"))

    def _build_headers(self) -> dict[str, str]:
        """
        Build the HTTP headers required for the Dev.to API.

        Includes the API key header if available.

        Returns:
            dict[str, str]: HTTP headers ready to use in each request.
        """
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["api-key"] = self.api_key
        return headers

    async def fetch_articles(self, limit: int) -> list[dict[str, Any]]:
        """
        Fetch the top articles from Dev.to sorted by popularity.

        Uses the /articles endpoint with per_page and top parameters
        to retrieve the most relevant articles.

        Args:
            limit (int): Number of articles to retrieve.

        Returns:
            list[dict[str, Any]]: A list of article dictionaries.

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        params = {
            "per_page": min(limit, 1000),  # Dev.to allows a maximum of 1000 per page
            "top": 7,                       # Articles trending in the last 7 days
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/articles",
                headers=self._build_headers(),
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def fetch_and_transform(self, limit: Optional[int] = None) -> list[RawItem]:
        """
        Main method to fetch top articles and transform them into RawItem instances.

        This is the primary entry point for fetching Dev.to articles.
        It orchestrates fetching articles and transforming them into
        the desired data structure.

        Args:
            limit (Optional[int]): Maximum number of articles to fetch.
                                   Defaults to max_articles if not provided.

        Returns:
            list[RawItem]: A list of RawItem instances containing Dev.to article data.
        """
        fetch_limit = limit or self.max_articles
        articles = await self.fetch_articles(fetch_limit)
        raw_items = transform_to_raw_items(articles)
        return raw_items