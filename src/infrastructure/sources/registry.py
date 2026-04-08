from infrastructure.sources.hacker_news import HackerNewsClient
from core.types.source import Source


hn_client = HackerNewsClient()


async def fetch_hacker_news():
    return await hn_client.fetch_and_transform()


SOURCES = [
    Source(
        name="hacker_news",
        category="dev",
        fetch=fetch_hacker_news,
    ),
]

def get_all_sources() -> list[Source]:
    return SOURCES