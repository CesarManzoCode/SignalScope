"""
Source registry module.

This module defines and registers all available content sources,
exposing them through a unified interface for the pipeline to consume.
"""

from infrastructure.sources.hacker_news import HackerNewsClient
from infrastructure.sources.github import GitHubClient
from infrastructure.sources.dev_to import DevToClient
from infrastructure.sources.arxiv import ArXivClient
from core.types.source import Source

hn_client = HackerNewsClient()
gh_client = GitHubClient()   # Token read from GITHUB_TOKEN env var
dt_client = DevToClient()    # API key read from DEVTO_API_KEY env var (optional)
ax_client = ArXivClient()    # Keywords read from config/user_config.json


async def fetch_hacker_news() -> list:
    return await hn_client.fetch_and_transform()


async def fetch_github() -> list:
    return await gh_client.fetch_and_transform()


async def fetch_dev_to() -> list:
    return await dt_client.fetch_and_transform()


async def fetch_arxiv() -> list:
    return await ax_client.fetch_and_transform()


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
    Source(
        name="dev_to",
        category="dev",
        fetch=fetch_dev_to,
    ),
    Source(
        name="arxiv",
        category="research",
        fetch=fetch_arxiv,
    ),
]


def get_all_sources() -> list[Source]:
    return SOURCES