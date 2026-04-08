import json
from typing import List

from core.types.raw_item import RawItem
from core.types.final_item import FinalItem
from infrastructure.llm_clients.base import LLMClient
from config.prompts.full_prompt import build_full_prompt

async def process_items(
    items: List[RawItem],
    llm_client: LLMClient,
    protocols: str = ""
) -> List[FinalItem]:
    """
    Process RawItems → FinalItems using LLM (JSON output).
    """
    results: List[FinalItem] = []

    for item in items:
        content = build_content(item)
        prompt = build_full_prompt(content, protocols)

        response = await llm_client.generate(prompt)
        parsed = safe_json_load(response)

        results.append(
            FinalItem(
                title=parsed.get("title", ""),
                summary=parsed.get("summary", ""),
                key_points=parsed.get("key_points", []),
                details=parsed.get("details", ""),
                source=item.source,
                url=item.url,
                priority=parsed.get("priority", "optional")
            )
        )

    return results


def build_content(item: RawItem) -> str:
    """
    Convert RawItem into plain text for prompting.
    """

    parts = [f"Title: {item.title}"]

    if item.summary:
        parts.append(f"Summary: {item.summary}")

    if item.url:
        parts.append(f"URL: {item.url}")

    return "\n".join(parts)


# -------------------------
# JSON Safety Layer
# -------------------------

def safe_json_load(text: str) -> dict:
    """
    Safely parse JSON from LLM output.
    Handles common formatting issues.
    """

    text = text.strip()

    # Remove Markdown code blocks if present
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from LLM:\n{text}") from e