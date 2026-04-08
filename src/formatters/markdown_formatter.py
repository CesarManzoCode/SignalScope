from pathlib import Path
from datetime import datetime
from typing import List

from core.types.final_item import FinalItem

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output"


def save_as_markdown(items: List[FinalItem]) -> Path:
    """
    Convert FinalItem objects into a Markdown report and save it.
    """

    OUTPUT_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = OUTPUT_DIR / f"report_{timestamp}.md"

    sections = []

    for item in items:
        sections.append(format_item(item))

    full_text = "\n\n---\n\n".join(sections)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    return file_path


# -------------------------
# Formatting logic
# -------------------------

def format_item(item: FinalItem) -> str:
    """
    Convert a FinalItem into Markdown format.
    """

    parts = [f"# {item.title}"]

    # Title

    # Summary
    if item.summary:
        parts.append("## Summary")
        parts.append(item.summary)

    # Key Points
    if item.key_points:
        parts.append("## Key Points")
        for point in item.key_points:
            parts.append(f"- {point}")

    # Details
    if item.details:
        parts.append("## Details")
        parts.append(item.details)

    # Metadata
    if item.url:
        parts.append(f"\n**Source:** {item.url}")

    # Priority:
    if item.priority:
        parts.append(f"\n**Priority:** {item.priority}")

    return "\n\n".join(parts)