from typing import Optional
import httpx

from core.types.llm_response import LLMResponse
from infrastructure.llm_clients.base import get_env, LLMClient


class OllamaClient(LLMClient):
    """
    Ollama local LLM client using HTTP API.
    """

    def __init__(self, model: Optional[str] = None):
        self.url = get_env("OLLAMA_URL", "http://localhost:11434")
        self.model = model or get_env("DEFAULT_MODEL", "llama3")

    async def generate(self, prompt: str) -> LLMResponse:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
            )

        response.raise_for_status()
        data = response.json()

        content = data.get("response", "")

        input_tokens = data.get("prompt_eval_count", 0)
        output_tokens = data.get("eval_count", 0)
        total_tokens = input_tokens + output_tokens

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )