from config.prompts.base_prompt import build_base_prompt
from config.prompts.summary_prompt import build_summary_prompt
from config.prompts.formatting_prompt import build_formatting_prompt
from config.prompts.protocols_prompt import build_protocols_prompt


def build_full_prompt(content: str, protocols: str = "") -> str:
    base = build_base_prompt()
    summary = build_summary_prompt(content)
    formatting = build_formatting_prompt(content)

    if protocols:
        protocol_block = build_protocols_prompt(protocols)
        return f"{base}\n{protocol_block}\n{summary}\n{formatting}"

    return f"{base}\n{summary}\n{formatting}"