from typing import List
from core.types.final_item import FinalItem


def create_final_items(raw_outputs: List[str]) -> List[FinalItem]:
    """
    Convert LLM outputs (strings) into structured FinalItem objects.
    """

    final_items = []

    for output in raw_outputs:
        title = extract_title(output)
        summary = extract_section(output, "Summary")
        key_points = extract_list(output, "Key Points")
        details = extract_section(output, "Details")

        final_items.append(
            FinalItem(
                title=title,
                summary=summary,
                key_points=key_points,
                details=details,
                source="",  # optional for now
                url=""      # optional for now
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