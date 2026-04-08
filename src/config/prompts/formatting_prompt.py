from config.prompts.base_prompt import build_base_prompt

def build_formatting_prompt(content: str) -> str:
    return f"""
{build_base_prompt()}

Your task is to transform the following content into a structured JSON object.

STRICT RULES:
- Output ONLY valid JSON
- Do NOT include explanations
- Do NOT include markdown
- Do NOT include comments
- Do NOT hallucinate or add information
- Use ONLY the provided content

JSON FORMAT:

{{
  "title": "...",
  "summary": "...",
  "key_points": ["...", "..."],
  "details": "..."
}}

Content:
{content}
"""