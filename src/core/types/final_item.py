from dataclasses import dataclass
from typing import List


@dataclass
class FinalItem:
    title: str
    summary: str
    key_points: List[str]
    details: str
    source: str
    url: str
    priority: str