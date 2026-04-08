from typing import List

from core.types.raw_item import RawItem
from infrastructure.llm_clients.base import LLMClient
from config.prompts.full_prompt import build_full_prompt


async def process_items(
    items: List[RawItem],
    llm_client: LLMClient,
    protocols: str = ""
) -> List[str]:
    """
    Process a list of RawItems using an LLM.

    Args:
        items: Raw input data
        llm_client: LLM client implementation
        protocols: Optional protocol rules

    Returns:
        List of processed text outputs
    """

    results = []

    for item in items:
        content = build_content(item)
        prompt = build_full_prompt(content, protocols)

        response = await llm_client.generate(prompt)
        results.append(response)

    return results


def build_content(item: RawItem) -> str:
    """
    Convert RawItem into plain text for prompting.
    """

    parts = [
        f"Title: {item.title}",
    ]

    if item.summary:
        parts.append(f"Summary: {item.summary}")

    if item.url:
        parts.append(f"URL: {item.url}")

    return "\n".join(parts)