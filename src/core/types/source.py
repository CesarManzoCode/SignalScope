from dataclasses import dataclass
from typing import Callable, Awaitable

from core.types.raw_item import RawItem


@dataclass
class Source:
    name: str
    category: str  # "dev" | "security"
    fetch: Callable[[], Awaitable[list[RawItem]]]