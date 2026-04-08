# core/types/llm_output.py
from dataclasses import dataclass
from typing import List

@dataclass
class LLMOutput:
    title: str
    summary: str
    key_points: List[str]
    details: str
    source: str
    url: str
    priority: str