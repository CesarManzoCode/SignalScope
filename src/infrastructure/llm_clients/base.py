from typing import Protocol, runtime_checkable

import os
from dotenv import load_dotenv

from core.types.llm_response import LLMResponse

load_dotenv()

def get_env(key: str, default: str | None = None) -> str:
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Missing environment variable: {key}")
    return value

@runtime_checkable
class LLMClient(Protocol):
    """
    Common interface for all LLM clients.

    Any LLM client must implement this interface to be compatible
    with the system.
    """

    async def generate(self, prompt: str) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            prompt (str): Input prompt.

        Returns:
            str: Generated text response.
        """
        ...