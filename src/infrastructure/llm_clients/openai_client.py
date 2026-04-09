from typing import Optional
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionUserMessageParam

from infrastructure.llm_clients.base import get_env, LLMClient
from core.types.llm_response import LLMResponse


class OpenAIClient(LLMClient):
    """
    OpenAI LLM client using async chat completions API.
    """

    def __init__(self, model: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=get_env("OPENAI_API_KEY"))
        self.model = model or get_env("DEFAULT_MODEL", "gpt-4.1-mini")

    async def generate(self, prompt: str) -> LLMResponse:
        messages: list[ChatCompletionUserMessageParam] = [
            {"role": "user", "content": prompt}
        ]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )

        content = response.choices[0].message.content or ""

        if response.usage:
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
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