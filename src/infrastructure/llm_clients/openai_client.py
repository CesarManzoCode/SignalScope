from typing import Optional
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionUserMessageParam


from infrastructure.llm_clients.base import get_env, LLMClient


class OpenAIClient(LLMClient):
    """
    OpenAI LLM client using async chat completions API.
    """

    def __init__(self, model: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=get_env("OPENAI_API_KEY"))
        self.model = model or get_env("DEFAULT_MODEL", "gpt-4.1-mini")

    async def generate(self, prompt: str) -> str:
        """
        Send a prompt to OpenAI and return the generated response.
        """
        messages: list[ChatCompletionUserMessageParam] = [
            {"role": "user", "content": prompt}
        ]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )

        content = response.choices[0].message.content
        return content or ""