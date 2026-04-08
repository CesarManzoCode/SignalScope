from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class RawItem:
    title: str
    summary: str
    url: str
    source: str
    tags: list[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    published_at: Optional[str] = None