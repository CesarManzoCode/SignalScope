from typing import Optional
from anthropic import AsyncAnthropic
from anthropic.types import MessageParam, TextBlock

from core.types.llm_response import LLMResponse
from infrastructure.llm_clients.base import get_env, LLMClient


class AnthropicClient(LLMClient):
    """
    Anthropic LLM client using messages API.
    """

    def __init__(self, model: Optional[str] = None):
        self.client = AsyncAnthropic(api_key=get_env("ANTHROPIC_API_KEY"))
        self.model = model or get_env("DEFAULT_MODEL", "claude-3-opus-20240229")

    async def generate(self, prompt: str) -> LLMResponse:
        """
        Send a prompt to Anthropic and return the generated response.
        """
        messages: list[MessageParam] = [
            {"role": "user", "content": prompt}
        ]

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=messages,
        )

        parts: list[str] = []

        for block in response.content:
            if isinstance(block, TextBlock):
                parts.append(block.text)

        content = "".join(parts)

        if response.usage:
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = input_tokens + output_tokens
        else:
            input_tokens = 0
            output_tokens = 0
            total_tokens = 0

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )