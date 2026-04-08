import asyncio
from core.types.raw_item import RawItem
from core.types.source import Source


async def run_research(sources: list[Source]) -> list[RawItem]:
    async def fetch_safe(source: Source) -> list[RawItem]:
        try:
            return await source.fetch()
        except Exception(BaseException):
            return []

    results = await asyncio.gather(*[fetch_safe(source) for source in sources])

    return [item for sublist in results for item in sublist]