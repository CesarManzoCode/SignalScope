def build_protocols_prompt(protocols: str) -> str:
    return f"""
Additional system protocols:

You MUST follow these rules:

{protocols}
"""