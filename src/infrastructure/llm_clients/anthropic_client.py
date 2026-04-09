from typing import Optional
from anthropic import AsyncAnthropic

from infrastructure.llm_clients.base import get_env, LLMClient


class AnthropicClient(LLMClient):
    """
    Anthropic LLM client using messages API.
    """

    def __init__(self, model: Optional[str] = None):
        self.client = AsyncAnthropic(api_key=get_env("ANTHROPIC_API_KEY"))
        self.model = model or get_env("DEFAULT_MODEL", "claude-3-opus-20240229")

    async def generate(self, prompt: str) -> str:
        """
        Send a prompt to Anthropic and return the generated response.
        """
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        return "".join(
            block.text for block in response.content if hasattr(block, "text")
        )