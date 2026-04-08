from typing import List
from core.types.llm_output import LLMOutput
from core.types.final_item import FinalItem


def create_final_items(raw_outputs: List[LLMOutput]) -> List[FinalItem]:
    return [
        FinalItem(
            title=o.title,
            summary=o.summary,
            key_points=o.key_points,
            details=o.details,
            source=o.source,
            url=o.url,
            priority=o.priority
        )
        for o in raw_outputs
    ]


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