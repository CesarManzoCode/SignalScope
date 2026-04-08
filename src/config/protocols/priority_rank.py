def build_priority_rank_protocol(mode: str) -> str:
    """
    Build the priority ranking protocol for the LLM.

    Args:
        mode: User mode ("dev" or "security")

    Returns:
        str: Protocol instructions for priority ranking.
    """

    base_rules = """
Priority Ranking Rules:

You must assign exactly one priority level to the content:
- critical
- important
- optional

Definitions:
- critical: Requires immediate attention. High urgency, high impact, or security risk.
- important: Relevant and useful, but not urgent.
- optional: Interesting or informative, but low urgency and low impact.

You must choose the priority level based only on the provided content.
Do not invent urgency if it is not supported by the input.
"""

    if mode == "security":
        mode_rules = """
Security-specific rules:
- Mark as critical if the content describes vulnerabilities, exploits, active security risks, system compromises, or urgent patches.
- Mark as important if the content is security-relevant but not immediately urgent.
- Mark as optional if the content is only informational or loosely related to security.
"""
    else:
        mode_rules = """
Developer-specific rules:
- Mark as critical if the content describes breaking changes, urgent vulnerabilities in widely used tools/frameworks, or major issues that may affect production systems.
- Mark as important if the content is highly relevant to developers, frameworks, tooling, infrastructure, or engineering workflows.
- Mark as optional if the content is only interesting, experimental, or low-impact.
"""

    output_rule = """
The JSON output must include a "priority" field.
Allowed values:
- "critical"
- "important"
- "optional"
"""

    return "\n".join([base_rules.strip(), mode_rules.strip(), output_rule.strip()])