from config.prompts.base_prompt import build_base_prompt

def build_formatting_prompt(content: str) -> str:
    return f"""
{build_base_prompt()}

Your task is to transform the following content into a structured technical report.

Instructions:
- Organize information logically
- Use clear sections and headings
- Keep content readable and well structured
- Do NOT add new information
- Do NOT remove important details
- Improve clarity and presentation

Output format (IMPORTANT):

# Title

## Summary
...

## Key Points
- ...
- ...

## Details
...

Content:
{content}
"""