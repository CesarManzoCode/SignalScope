from typing import Optional
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


class OpenAIClient:
    """
    OpenAI LLM client using async chat completions API.
    """

    def __init__(self, model: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model or os.getenv("DEFAULT_MODEL", "gpt-4.1-mini")

    async def generate(self, prompt: str) -> str:
        """
        Send a prompt to OpenAI and return the generated response.
        """
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.choices[0].message.content
        return content or ""