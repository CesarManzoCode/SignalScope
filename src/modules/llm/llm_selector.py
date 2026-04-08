from infrastructure.llm_clients.openai_client import OpenAIClient
from infrastructure.llm_clients.anthropic_client import AnthropicClient
from infrastructure.llm_clients.ollama import OllamaClient


def get_llm_client(config: dict):
    provider = config.get("llm", {}).get("provider", "openai")

    if provider == "openai":
        return OpenAIClient()

    if provider == "anthropic":
        return AnthropicClient()

    if provider == "ollama":
        return OllamaClient()

    raise ValueError(f"Unsupported LLM provider: {provider}")