import logging
from core.types.raw_item import RawItem
from typing import Any

logger = logging.getLogger(__name__)

def filter_items(items: list[RawItem], config: dict[str, Any]) -> list[RawItem]:
    if not isinstance(items, list):
        raise TypeError(f"'items' must be list, received: {type(items).__name__}")

    if not isinstance(config, dict):
        raise TypeError(f"'config' must be dict, received: {type(config).__name__}")

    technologies = config.get("technologies", [])

    if not isinstance(technologies, list):
        raise TypeError(f"'technologies' must be list, received: {type(technologies).__name__}")

    if not technologies:
        return list(items)

    filtered = []

    for item in items:
        try:
            title = getattr(item, "title", "") or ""
            summary = getattr(item, "summary", "") or ""
            if not isinstance(title, str):
                title = str(title)
            if not isinstance(summary, str):
                summary = str(summary)

            text = (title+ " " + summary).lower()

            if any(tech.lower() in text for tech in technologies):
                filtered.append(item)
        except Exception as e:
            logger.error("Error while filtering item (title=%s): %s", getattr(item, "title", "unknown"), e, exc_info=True)
            continue

    logger.debug("Filtered %s/%s items", len(filtered), len(items))
    return filtered