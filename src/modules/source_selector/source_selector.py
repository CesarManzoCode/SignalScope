from typing import Any
from core.types.source import Source


def select_sources(sources: list[Source], config: dict[str, Any]) -> list[Source]:
    mode = config.get("mode") or "dev"

    got_sources = config.get("sources") or {}
    include_list = got_sources.get("include") or []
    exclude_list = got_sources.get("exclude") or []

    if include_list:
        filtered = [s for s in sources if s.name in include_list]
    else:
        filtered = [s for s in sources if s.category == mode]

    if exclude_list:
        filtered = [s for s in filtered if s.name not in exclude_list]

    return filtered