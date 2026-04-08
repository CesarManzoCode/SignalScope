"""
ArXiv API client module.

This module provides functionality to fetch papers from the ArXiv API
using keywords extracted from the user configuration file, and structures
them into RawItem data classes for consistent handling.
"""

import httpx
import xml.etree.ElementTree as ET
from typing import Optional, Any
from dataclasses import dataclass, field
import json
import os

from core.types.raw_item import RawItem

# ArXiv Atom feed XML namespace
ARXIV_NAMESPACE = "http://www.w3.org/2005/Atom"

# ArXiv categories to search within
TARGET_CATEGORIES = ["cs.AI"]

# Path to the user configuration file
USER_CONFIG_PATH = os.path.join("config", "user_config.json")


def load_search_keywords() -> list[str]:
    """
    Load search keywords from the user configuration file.

    Combines 'technologies' and 'topics' fields from user_config.json
    into a single deduplicated keyword list used to query the ArXiv API.

    Returns:
        list[str]: A list of unique keywords for the search query.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        json.JSONDecodeError: If the configuration file is malformed.
    """
    with open(USER_CONFIG_PATH, "r", encoding="utf-8") as config_file:
        config: dict[str, Any] = json.load(config_file)

    technologies: list[str] = config.get("technologies", [])
    topics: list[str] = config.get("topics", [])

    # Combine and deduplicate while preserving order
    seen: set[str] = set()
    keywords: list[str] = []
    for keyword in technologies + topics:
        if keyword not in seen:
            seen.add(keyword)
            keywords.append(keyword)

    return keywords


def _parse_xml_response(xml_content: str) -> list[dict[str, Any]]:
    """
    Parse the ArXiv Atom XML response into a list of paper dictionaries.

    Extracts title, summary, authors, published date, URL, and categories
    from each entry in the Atom feed.

    Args:
        xml_content (str): Raw XML string returned by the ArXiv API.

    Returns:
        list[dict[str, Any]]: A list of dictionaries representing each paper.
    """
    root = ET.fromstring(xml_content)
    papers: list[dict[str, Any]] = []

    for entry in root.findall(f"{{{ARXIV_NAMESPACE}}}entry"):
        # Extract paper ID from the full ArXiv URL
        entry_id = entry.findtext(f"{{{ARXIV_NAMESPACE}}}id", default="")
        arxiv_id = entry_id.split("/abs/")[-1] if "/abs/" in entry_id else entry_id

        # Extract authors as a list of name strings
        authors: list[str] = [
            author.findtext(f"{{{ARXIV_NAMESPACE}}}name", default="Unknown")
            for author in entry.findall(f"{{{ARXIV_NAMESPACE}}}author")
        ]

        # Extract categories as a list of term strings
        categories: list[str] = [
            category.get("term", "")
            for category in entry.findall(f"{{{ARXIV_NAMESPACE}}}category")
            if category.get("term")
        ]

        papers.append({
            "arxiv_id": arxiv_id,
            "title": (entry.findtext(f"{{{ARXIV_NAMESPACE}}}title") or "Untitled").strip(),
            "summary": (entry.findtext(f"{{{ARXIV_NAMESPACE}}}summary") or "").strip(),
            "url": entry_id.strip(),
            "published_at": entry.findtext(f"{{{ARXIV_NAMESPACE}}}published"),
            "updated_at": entry.findtext(f"{{{ARXIV_NAMESPACE}}}updated"),
            "authors": authors,
            "categories": categories,
        })

    return papers


def transform_to_raw_items(papers: list[dict[str, Any]]) -> list[RawItem]:
    """
    Transform raw ArXiv paper dictionaries into RawItem instances.

    This method maps parsed ArXiv feed entries to the RawItem data class,
    extracting relevant fields and providing sensible defaults.

    Args:
        papers (list[dict[str, Any]]): Parsed paper dictionaries from the ArXiv feed.

    Returns:
        list[RawItem]: A list of RawItem instances populated with paper data.
    """
    raw_items = []

    for paper in papers:
        # Use ArXiv categories as tags alongside source identifiers
        tags = ["arxiv", "paper"] + paper.get("categories", [])

        # Build metadata dictionary with additional ArXiv fields
        metadata = {
            "arxiv_id": paper.get("arxiv_id"),
            "authors": paper.get("authors", []),
            "categories": paper.get("categories", []),
            "updated_at": paper.get("updated_at"),
        }

        raw_item = RawItem(
            title=paper.get("title", "Untitled"),
            summary=paper.get("summary", ""),
            url=paper.get("url", ""),
            source="arxiv",
            tags=tags,
            metadata=metadata,
            published_at=paper.get("published_at"),  # Already in ISO 8601 format
        )

        raw_items.append(raw_item)

    return raw_items


@dataclass
class ArXivClient:
    """
    Client for interacting with the ArXiv Atom Feed API.

    Attributes:
        base_url (str): The base URL for the ArXiv API.
        timeout (float): Request timeout in seconds.
        max_papers (int): Maximum number of papers to fetch.
        categories (list[str]): ArXiv categories to search within.
    """

    base_url: str = "https://export.arxiv.org/api/query"
    timeout: float = 15.0
    max_papers: int = 30
    categories: list[str] = field(default_factory=lambda: TARGET_CATEGORIES)

    def _build_search_query(self, keywords: list[str]) -> str:
        """
        Build the ArXiv search query string from keywords and target categories.

        Combines keywords with OR logic inside a ti_abs group (title + abstract),
        then restricts results to the configured categories using AND.

        Args:
            keywords (list[str]): Keywords extracted from the user configuration.

        Returns:
            str: A fully formed ArXiv search query string.
        """
        # Join keywords with OR to match any of them in title or abstract
        keyword_query = " OR ".join(
            f'ti_abs:"{keyword}"' for keyword in keywords
        )

        # Restrict to target categories with OR logic
        category_query = " OR ".join(
            f"cat:{category}" for category in self.categories
        )

        return f"({keyword_query}) AND ({category_query})"

    async def fetch_papers(self, keywords: list[str], limit: int) -> list[dict[str, Any]]:
        """
        Fetch papers from the ArXiv API matching the given keywords.

        Sends a GET request to the ArXiv Atom feed endpoint and parses
        the XML response into a list of paper dictionaries.

        Args:
            keywords (list[str]): Keywords to search for.
            limit (int): Maximum number of papers to retrieve.

        Returns:
            list[dict[str, Any]]: A list of parsed paper dictionaries.

        Raises:
            httpx.HTTPError: If the API request fails.
        """
        params = {
            "search_query": self._build_search_query(keywords),
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            return _parse_xml_response(response.text)

    async def fetch_and_transform(self, limit: Optional[int] = None) -> list[RawItem]:
        """
        Main method to fetch relevant papers and transform them into RawItem instances.

        This is the primary entry point for fetching ArXiv papers.
        It loads keywords from the user configuration, fetches matching papers,
        and transforms them into the desired data structure.

        Args:
            limit (Optional[int]): Maximum number of papers to fetch.
                                   Defaults to max_papers if not provided.

        Returns:
            list[RawItem]: A list of RawItem instances containing ArXiv paper data.
        """
        fetch_limit = limit or self.max_papers
        keywords = load_search_keywords()
        papers = await self.fetch_papers(keywords, fetch_limit)
        raw_items = transform_to_raw_items(papers)
        return raw_items