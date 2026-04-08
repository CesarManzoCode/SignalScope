"""
Hacker News API client module.

This module provides functionality to fetch stories from the Hacker News API
and structure them into RawItem data classes for consistent handling.
"""

import httpx
import asyncio
from typing import Optional, Any
from dataclasses import dataclass

from core.types.raw_item import RawItem


@dataclass
class HackerNewsClient:
    """
    Client for interacting with the Hacker News Firebase API.

    Attributes:
        base_url (str): The base URL for the Hacker News API.
        timeout (float): Request timeout in seconds.
        max_stories (int): Maximum number of stories to fetch.
    """

    base_url: str = "https://hacker-news.firebaseio.com/v0"
    timeout: float = 10.0
    max_stories: int = 30

    async def fetch_top_story_ids(self, limit: int) -> list[int]:
        """
        Fetch the IDs of top stories from Hacker News.

        Args:
            limit (int): Number of story IDs to retrieve.

        Returns:
            list[int]: A list of story IDs.

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/topstories.json")
            response.raise_for_status()
            story_ids = response.json()
            return story_ids[:limit]

    async def fetch_item(self, client: httpx.AsyncClient, item_id: int) -> Optional[dict[str, Any]]:
        """
        Fetch a single item from Hacker News by its ID.

        Args:
            client (httpx.AsyncClient): Shared HTTP client.
            item_id (int): The ID of the item to fetch.

        Returns:
            Optional[dict[str, Any]]: The item data as a dictionary, or None if fetch fails.
        """
        try:
            response = await client.get(f"{self.base_url}/item/{item_id}.json")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as error:
            print(f"Failed to fetch item {item_id}: {error}")
            return None

    async def fetch_items_batch(self, item_ids: list[int]) -> list[dict[str, Any]]:
        """
        Fetch multiple items concurrently from Hacker News.

        Args:
            item_ids (list[int]): A list of item IDs to fetch.

        Returns:
            list[dict[str, Any]]: A list of item dictionaries.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tasks = [self.fetch_item(client, item_id) for item_id in item_ids]
            results = await asyncio.gather(*tasks)
        return [item for item in results if item is not None]

    def transform_to_raw_items(self, items: list[dict[str, Any]]) -> list[RawItem]:
        """
        Transform raw Hacker News items into RawItem instances.

        This method maps Hacker News API responses to the RawItem data class,
        extracting relevant fields and providing sensible defaults.

        Args:
            items (list[dict[str, Any]]): Raw item dictionaries from Hacker News API.

        Returns:
            list: A list of RawItem instances populated with story data.
        """
        from core.types.raw_item import RawItem
        raw_items = []

        for item in items:
            # Extract title with fallback
            title = item.get("title", "Untitled")

            # Extract URL with fallback
            url = item.get("url", "")

            # Extract source domain from URL if available
            source = "hacker_news"

            # Use item text as summary if available, otherwise use title
            summary = item.get("text") or ""
            # Build metadata dictionary with additional Hacker News fields
            metadata = {
                "story_id": item.get("id"),
                "score": item.get("score", 0),
                "comment_count": item.get("descendants", 0),
                "author": item.get("by", "Anonymous"),
                "item_type": item.get("type", "story"),
            }

            # Create RawItem instance
            raw_item = RawItem(
                title=title,
                summary=summary,
                url=url,
                source=source,
                tags=["hacker_news", item.get("type", "story")],
                metadata=metadata,
                published_at=self._format_timestamp(item.get("time")),
            )

            raw_items.append(raw_item)

        return raw_items

    @staticmethod
    def _format_timestamp(unix_timestamp: Optional[int]) -> Optional[str]:
        """
        Convert Unix timestamp to ISO 8601 format string.

        Args:
            unix_timestamp (Optional[int]): Unix timestamp in seconds.

        Returns:
            Optional[str]: ISO 8601 formatted datetime string, or None if input is None.
        """
        if unix_timestamp is None:
            return None

        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
        return dt.isoformat()

    async def fetch_and_transform(self, limit: Optional[int] = None) -> list[RawItem]:
        """
        Main method to fetch top stories and transform them into RawItem instances.

        This is the primary entry point for fetching Hacker News stories.
        It orchestrates fetching story IDs, fetching individual items,
        and transforming them into the desired data structure.

        Args:
            limit (Optional[int]): Maximum number of stories to fetch.
                                   Defaults to max_stories if not provided.

        Returns:
            list: A list of RawItem instances containing Hacker News stories.
        """
        fetch_limit = limit or self.max_stories
        story_ids = await self.fetch_top_story_ids(fetch_limit)
        items = await self.fetch_items_batch(story_ids)
        raw_items = self.transform_to_raw_items(items)
        return raw_items