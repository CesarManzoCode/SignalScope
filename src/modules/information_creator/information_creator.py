from typing import List
import json
from core.types.final_item import FinalItem


def create_final_items(raw_outputs: List[str]) -> List[FinalItem]:
    final_items = []

    for output in raw_outputs:
        text = output.strip()
        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(text)

        final_items.append(
            FinalItem(
                title=parsed.get("title", ""),
                summary=parsed.get("summary", ""),
                key_points=parsed.get("key_points", []),
                details=parsed.get("details", ""),
                source="",
                url="",
                priority=parsed.get("priority", "optional")
            )
        )

    return final_items


# -------------------------
# Helpers (simple parsing)
# -------------------------

def extract_title(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line.replace("# ", "").strip()
    return ""


def extract_section(text: str, section_name: str) -> str:
    lines = text.splitlines()
    capture = False
    collected = []

    for line in lines:
        if line.strip().startswith(f"## {section_name}"):
            capture = True
            continue

        if capture:
            if line.startswith("## "):  # next section
                break
            collected.append(line)

    return "\n".join(collected).strip()


def extract_list(text: str, section_name: str) -> List[str]:
    section = extract_section(text, section_name)
    return [
        line.replace("- ", "").strip()
        for line in section.splitlines()
        if line.strip().startswith("- ")
    ]