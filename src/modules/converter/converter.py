from typing import List
from pathlib import Path

from core.types.final_item import FinalItem
from formatters.markdown_formatter import save_as_markdown


def convert(items: List[FinalItem], config: dict) -> Path:
    """
    Convert FinalItems into the desired output format based on config.
    """

    format_type = config.get("output", {}).get("format", "markdown")

    if format_type == "markdown":
        return save_as_markdown(items)

    raise ValueError(f"Unsupported output format: {format_type}")