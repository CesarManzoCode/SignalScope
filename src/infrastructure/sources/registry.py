"""
Source registry module.

This module defines and registers all available content sources,
exposing them through a unified interface for the pipeline to consume.
"""

from infrastructure.sources.hacker_news import HackerNewsClient
from infrastructure.sources.github import GitHubClient
from core.types.source import Source

hn_client = HackerNewsClient()
gh_client = GitHubClient()


async def fetch_hacker_news() -> list:
    return await hn_client.fetch_and_transform()


async def fetch_github() -> list:
    return await gh_client.fetch_and_transform()


SOURCES = [
    Source(
        name="hacker_news",
        category="dev",
        fetch=fetch_hacker_news,
    ),
    Source(
        name="github",
        category="dev",
        fetch=fetch_github,
    ),
]


def get_all_sources() -> list[Source]:
    return SOURCES