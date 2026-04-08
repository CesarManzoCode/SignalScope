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

    def __str__(self):
        return f"{self.title} {self.summary} {self.key_points} {self.details}"