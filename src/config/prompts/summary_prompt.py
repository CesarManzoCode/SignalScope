from config.prompts.base_prompt import build_base_prompt

def build_summary_prompt(content: str) -> str:
    return f"""
{build_base_prompt()}

Your task is to summarize the following technical content.

Instructions:
- Extract only the most important technical insights
- Remove irrelevant or non-technical information
- Keep it concise and clear
- Do NOT omit critical details
- Do NOT add new information

Content:
{content}
"""