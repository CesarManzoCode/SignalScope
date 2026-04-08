from dataclasses import dataclass
from typing import Callable, Awaitable


@dataclass
class RawItem:
    pass


@dataclass
class Source:
    name: str
    category: str
    fetch: Callable[[], Awaitable[list[RawItem]]]


def select_sources(sources: list[Source], config: dict) -> list[Source]:
    mode = config.get("mode", "dev")
    include_list = config.get("sources", {}).get("include", [])
    exclude_list = config.get("sources", {}).get("exclude", [])

    if include_list:
        filtered = [s for s in sources if s.name in include_list]
    else:
        filtered = [s for s in sources if s.category == mode]

    if exclude_list:
        filtered = [s for s in filtered if s.name not in exclude_list]

    return filtered