"""
LLM client factory with advanced error handling and robustness.
Resolves the appropriate client implementation based on the provided configuration.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

from infrastructure.llm_clients.openai_client import OpenAIClient
from infrastructure.llm_clients.anthropic_client import AnthropicClient
from infrastructure.llm_clients.ollama import OllamaClient

if TYPE_CHECKING:
    from infrastructure.llm_clients.base import LLMClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SUPPORTED_PROVIDERS: Final[frozenset[str]] = frozenset({"openai", "anthropic", "ollama"})
_DEFAULT_PROVIDER: Final[str] = "openai"

# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_llm_client(config: dict) -> "LLMClient":
    """
    Resolve and instantiate the LLM client specified in *config*.

    Parameters
    ----------
    config:
        Application configuration dictionary. Expected shape::

            {
                "llm": {
                    "provider": "openai" | "anthropic" | "ollama"
                }
            }

    Returns
    -------
    BaseLLMClient
        A fully-initialized LLM client ready for use.

    Raises
    ------
    TypeError
        If *config* is not a dict.
    ValueError
        If the resolved provider name is empty, not a string, or not supported.
    RuntimeError
        If the client class raises an unexpected exception during instantiation.
    """
    # ------------------------------------------------------------------
    # 1. Guard: config must be a plain mapping
    # ------------------------------------------------------------------
    if not isinstance(config, dict):
        raise TypeError(
            f"'config' must be a dict, got {type(config).__name__!r}."
        )

    # ------------------------------------------------------------------
    # 2. Resolve provider name
    # ------------------------------------------------------------------
    llm_section = config.get("llm")

    if llm_section is None:
        logger.warning(
            "Key 'llm' is absent from config — falling back to default provider %r.",
            _DEFAULT_PROVIDER,
        )
        llm_section = {}

    if not isinstance(llm_section, dict):
        raise TypeError(
            f"config['llm'] must be a dict, got {type(llm_section).__name__!r}."
        )

    raw_provider = llm_section.get("provider", _DEFAULT_PROVIDER)

    if raw_provider is None:
        logger.warning(
            "config['llm']['provider'] is None — falling back to default provider %r.",
            _DEFAULT_PROVIDER,
        )
        raw_provider = _DEFAULT_PROVIDER

    if not isinstance(raw_provider, str):
        raise TypeError(
            f"config['llm']['provider'] must be a str, got {type(raw_provider).__name__!r}."
        )

    provider = raw_provider.strip().lower()

    if not provider:
        raise ValueError(
            "config['llm']['provider'] resolved to an empty string after stripping whitespace."
        )

    # ------------------------------------------------------------------
    # 3. Validate against the supported set
    # ------------------------------------------------------------------
    if provider not in _SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unsupported LLM provider: {provider!r}. "
            f"Supported providers are: {sorted(_SUPPORTED_PROVIDERS)}."
        )

    # ------------------------------------------------------------------
    # 4. Instantiate the client
    # ------------------------------------------------------------------
    logger.debug("Instantiating LLM client for provider %r.", provider)

    try:
        if provider == "openai":
            client = OpenAIClient()
        elif provider == "anthropic":
            client = AnthropicClient()
        elif provider == "ollama":
            client = OllamaClient()
        # The exhaustive check above makes this branch unreachable,
        # but it keeps static analyzers and future maintainers happy.
        else:  # pragma: no cover
            raise ValueError(f"Unsupported LLM provider: {provider!r}.")

    except (ValueError, TypeError):
        # Re-raise domain errors as-is so callers can discriminate them.
        raise
    except Exception as exc:
        raise RuntimeError(
            f"Unexpected error while instantiating the {provider!r} LLM client: {exc}"
        ) from exc

    logger.info("LLM client for provider %r instantiated successfully.", provider)
    return client