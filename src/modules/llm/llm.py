"""
Item processing pipeline: RawItem → FinalItem via LLM with JSON output.

This module handles the full transformation lifecycle of raw items into
structured FinalItems using an LLM client. It is designed for production
resilience: every failure mode is caught, classified, and surfaced with
full context so callers can react appropriately.
"""

from __future__ import annotations

import json
import logging
import re
import textwrap
from typing import List, Optional

from core.types.raw_item import RawItem
from core.types.final_item import FinalItem
from infrastructure.llm_clients.base import LLMClient
from config.prompts.full_prompt import build_full_prompt

# ---------------------------------------------------------------------------
# Module-level logger — callers can attach handlers / set levels externally.
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class ItemProcessingError(Exception):
    """
    Raised when a single RawItem cannot be processed after all recovery
    attempts have been exhausted.

    Attributes:
        item_title: Human-readable identifier for the failing item.
        original_error: The root cause exception, if available.
    """

    def __init__(
        self,
        message: str,
        item_title: str = "<unknown>",
        original_error: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message)
        self.item_title = item_title
        self.original_error = original_error

    def __str__(self) -> str:  # noqa: D105
        base = super().__str__()
        if self.original_error:
            return f"{base} | caused by: {type(self.original_error).__name__}: {self.original_error}"
        return base


class LLMResponseParsingError(ItemProcessingError):
    """
    Specialisation of ItemProcessingError for JSON parsing failures.

    Attributes:
        raw_text: The exact string returned by the LLM that could not be parsed.
    """

    def __init__(
        self,
        message: str,
        raw_text: str = "",
        item_title: str = "<unknown>",
        original_error: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message, item_title=item_title, original_error=original_error)
        self.raw_text = raw_text

    def __str__(self) -> str:  # noqa: D105
        base = super().__str__()
        truncated = textwrap.shorten(self.raw_text, width=200, placeholder="…")
        return f"{base} | raw_text_preview: {truncated!r}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def process_items(
    items: List[RawItem],
    llm_client: LLMClient,
    protocols: str = "",
) -> List[FinalItem]:
    """
    Transform a list of RawItems into FinalItems using an LLM for enrichment.

    Each item is processed independently so that one failure does not abort
    the entire batch.  Successfully processed items are always returned even
    when some items fail.

    Args:
        items: Non-empty list of raw items to process.
        llm_client: Concrete LLM client instance; must implement `generate`.
        protocols: Optional protocol/instruction string forwarded to the prompt
                   builder. Defaults to an empty string (no extra protocols).

    Returns:
        List of FinalItem instances, one per successfully processed RawItem.
        Items that fail processing are excluded from the result and logged at
        ERROR level with full context.

    Raises:
        TypeError: If `items` is not a list or `llm_client` is None.
        ValueError: If `items` is an empty list.
    """
    # ---- Pre-condition guards -----------------------------------------------
    if not isinstance(items, list):
        raise TypeError(
            f"'items' must be a list, got {type(items).__name__!r} instead."
        )
    if items is None or len(items) == 0:
        raise ValueError("'items' must contain at least one RawItem to process.")
    if llm_client is None:
        raise TypeError("'llm_client' must not be None.")

    # ---- Batch processing ---------------------------------------------------
    results: List[FinalItem] = []
    failed_count: int = 0
    total_count: int = len(items)

    logger.info("Starting batch processing — %d item(s) to process.", total_count)

    for index, item in enumerate(items):
        item_label = _safe_item_title(item, index)
        logger.debug("Processing item %d/%d: %r", index + 1, total_count, item_label)

        try:
            final_item = await _process_single_item(item, llm_client, protocols)
            results.append(final_item)
            logger.debug(
                "Item %d/%d processed successfully: %r",
                index + 1,
                total_count,
                item_label,
            )

        except ItemProcessingError as exc:
            # Known, structured failure — log with full context and continue.
            failed_count += 1
            logger.error(
                "Failed to process item %d/%d (%r): %s",
                index + 1,
                total_count,
                item_label,
                exc,
                exc_info=True,
            )

        except Exception as exc:  # noqa: BLE001 — catch-all safety net
            # Unexpected failure — wrap it so the rest of the batch continues.
            failed_count += 1
            logger.error(
                "Unexpected error while processing item %d/%d (%r): %s",
                index + 1,
                total_count,
                item_label,
                exc,
                exc_info=True,
            )

    # ---- Post-batch summary -------------------------------------------------
    logger.info(
        "Batch complete — %d succeeded, %d failed out of %d total.",
        len(results),
        failed_count,
        total_count,
    )

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _process_single_item(
    item: RawItem,
    llm_client: LLMClient,
    protocols: str,
) -> FinalItem:
    """
    Handle the full processing lifecycle for one RawItem.

    Performs content building, prompt construction, LLM invocation, and
    JSON parsing.  All failures are re-raised as ItemProcessingError
    subclasses so the caller can handle them uniformly.

    Args:
        item: The raw item to enrich.
        llm_client: LLM client used for generation.
        protocols: Protocol/instruction string passed to the prompt builder.

    Returns:
        A fully populated FinalItem.

    Raises:
        ItemProcessingError: On LLM call failure or any other unexpected error.
        LLMResponseParsingError: When the LLM returns a response that cannot
                                  be parsed as valid JSON.
    """
    item_title = _safe_item_title(item)

    # ---- Step 1: Build prompt content ---------------------------------------
    try:
        content = build_content(item)
    except Exception as exc:
        raise ItemProcessingError(
            "Failed to build content string from RawItem.",
            item_title=item_title,
            original_error=exc,
        ) from exc

    if not content or not content.strip():
        raise ItemProcessingError(
            "build_content returned an empty string; cannot construct a prompt.",
            item_title=item_title,
        )

    # ---- Step 2: Build full prompt ------------------------------------------
    try:
        prompt = build_full_prompt(content, protocols)
    except Exception as exc:
        raise ItemProcessingError(
            "Failed to build the full LLM prompt.",
            item_title=item_title,
            original_error=exc,
        ) from exc

    if not prompt or not prompt.strip():
        raise ItemProcessingError(
            "build_full_prompt returned an empty prompt; aborting LLM call.",
            item_title=item_title,
        )

    # ---- Step 3: LLM call ---------------------------------------------------
    try:
        response = await llm_client.generate(prompt)
    except Exception as exc:
        raise ItemProcessingError(
            "LLM client raised an exception during generation.",
            item_title=item_title,
            original_error=exc,
        ) from exc

    # Defensive check: response object must exist and carry content.
    if response is None:
        raise ItemProcessingError(
            "LLM client returned None instead of a response object.",
            item_title=item_title,
        )

    raw_content: str = getattr(response, "content", None) or ""
    if not raw_content.strip():
        raise ItemProcessingError(
            "LLM response content is empty or whitespace-only.",
            item_title=item_title,
        )

    # ---- Step 4: Parse JSON from LLM output ---------------------------------
    try:
        parsed = safe_json_load(raw_content)
    except LLMResponseParsingError:
        # Already has full context — re-attach item title and re-raise.
        raise LLMResponseParsingError(
            "LLM output could not be parsed as JSON.",
            raw_text=raw_content,
            item_title=item_title,
        )
    except Exception as exc:
        raise LLMResponseParsingError(
            "Unexpected error while parsing LLM JSON output.",
            raw_text=raw_content,
            item_title=item_title,
            original_error=exc,
        ) from exc

    if not isinstance(parsed, dict):
        raise LLMResponseParsingError(
            f"Expected a JSON object at the top level, got {type(parsed).__name__!r}.",
            raw_text=raw_content,
            item_title=item_title,
        )

    # ---- Step 5: Assemble FinalItem -----------------------------------------
    total_tokens: int = getattr(response, "total_tokens", 0) or 0

    try:
        return FinalItem(
            title=_coerce_str(parsed.get("title"), fallback=""),
            summary=_coerce_str(parsed.get("summary"), fallback=""),
            key_points=_coerce_list(parsed.get("key_points")),
            details=_coerce_str(parsed.get("details"), fallback=""),
            source=getattr(item, "source", ""),
            url=getattr(item, "url", ""),
            priority=_coerce_str(parsed.get("priority"), fallback="optional"),
            tokens=total_tokens,
        )
    except Exception as exc:
        raise ItemProcessingError(
            "Failed to construct FinalItem from parsed LLM response.",
            item_title=item_title,
            original_error=exc,
        ) from exc


def build_content(item: RawItem) -> str:
    """
    Serialize a RawItem into a plain-text block suitable for LLM prompting.

    Only non-empty fields are included to keep the prompt concise.

    Args:
        item: The raw item to serialize.

    Returns:
        A newline-joined string with the item's fields.

    Raises:
        AttributeError: If `item` does not expose the expected attributes.
        TypeError: If `item` is None.
    """
    if item is None:
        raise TypeError("'item' must not be None.")

    # `item.title` is required — fail loudly if absent or non-string.
    title_value = getattr(item, "title", None)
    if not isinstance(title_value, str):
        raise AttributeError(
            f"RawItem.title must be a str, got {type(title_value).__name__!r}."
        )

    parts: List[str] = [f"Title: {title_value}"]

    summary_value = getattr(item, "summary", None)
    if summary_value and isinstance(summary_value, str) and summary_value.strip():
        parts.append(f"Summary: {summary_value.strip()}")

    url_value = getattr(item, "url", None)
    if url_value and isinstance(url_value, str) and url_value.strip():
        parts.append(f"URL: {url_value.strip()}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# JSON safety layer
# ---------------------------------------------------------------------------

# Compiled pattern for stripping Markdown fenced code blocks.
_MARKDOWN_FENCE_RE = re.compile(
    r"^```(?:json)?\s*\n?(.*?)\n?```\s*$",
    re.DOTALL | re.IGNORECASE,
)


def safe_json_load(text: str) -> dict:
    """
    Safely parse JSON from potentially messy LLM output.

    Applies a sequence of cleaning strategies before attempting to parse:
      1. Strip surrounding whitespace.
      2. Remove Markdown fenced code blocks (```json ... ``` or ``` ... ```).
      3. Locate the first ``{`` … last ``}`` substring as a last-resort
         extraction when the LLM wraps JSON in prose.

    Args:
        text: Raw string returned by the LLM.

    Returns:
        Parsed Python dictionary.

    Raises:
        TypeError: If `text` is not a string.
        ValueError: If `text` is empty after stripping.
        LLMResponseParsingError: If the text cannot be parsed as JSON after
                                  all cleaning strategies are exhausted.
    """
    if not isinstance(text, str):
        raise TypeError(
            f"safe_json_load expects a str, got {type(text).__name__!r}."
        )

    cleaned = text.strip()

    if not cleaned:
        raise ValueError("Cannot parse JSON from an empty string.")

    # ---- Strategy 1: strip Markdown fences ----------------------------------
    fence_match = _MARKDOWN_FENCE_RE.match(cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()
        logger.debug("safe_json_load: Markdown fence stripped from LLM output.")

    # Fallback simple strip for cases the regex does not cover.
    elif cleaned.startswith("```"):
        cleaned = re.sub(r"```(?:json)?", "", cleaned).replace("```", "").strip()
        logger.debug("safe_json_load: Applied fallback Markdown strip.")

    # ---- Strategy 2: direct parse -------------------------------------------
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as first_exc:
        logger.debug(
            "safe_json_load: Direct JSON parse failed (%s). Trying substring extraction.",
            first_exc,
        )

    # ---- Strategy 3: extract first JSON object from prose -------------------
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")

    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        candidate = cleaned[start_idx : end_idx + 1]
        try:
            parsed = json.loads(candidate)
            logger.warning(
                "safe_json_load: JSON was embedded in prose — extracted substring successfully."
            )
            return parsed
        except json.JSONDecodeError as second_exc:
            raise LLMResponseParsingError(
                "JSON substring extraction also failed; the LLM output is not recoverable.",
                raw_text=text,
                original_error=second_exc,
            ) from second_exc

    # ---- All strategies exhausted -------------------------------------------
    raise LLMResponseParsingError(
        "No JSON object found in LLM output after all cleaning strategies.",
        raw_text=text,
    )


# ---------------------------------------------------------------------------
# Private coercion utilities
# ---------------------------------------------------------------------------

def _coerce_str(value: object, *, fallback: str = "") -> str:
    """
    Safely coerce `value` to str, returning `fallback` for None or non-string types.

    Args:
        value: Value to coerce, typically from a parsed JSON dict.
        fallback: Default string returned when value is None or not a str.

    Returns:
        String representation or the fallback.
    """
    if value is None:
        return fallback
    if isinstance(value, str):
        return value
    # Attempt a best-effort conversion for numeric/bool scalars.
    # noinspection PyBroadException
    try:
        return str(value)
    except Exception:
        return fallback


def _coerce_list(value: object) -> list:
    """
    Safely coerce `value` to a list, returning an empty list as the fallback.

    Args:
        value: Value to coerce, typically from a parsed JSON dict.

    Returns:
        List, guaranteed to never be None.
    """
    if isinstance(value, list):
        return value
    if value is None:
        return []
    # Wrap scalar values so downstream code always gets a list.
    return [value]


def _safe_item_title(item: object, index: Optional[int] = None) -> str:
    """
    Extract a human-readable label from a RawItem for use in log messages.

    Never raises — always returns a string.

    Args:
        item: The item to inspect.
        index: Optional positional index used as a fallback label.

    Returns:
        Title string or a generic positional label.
    """
    # noinspection PyBroadException
    try:
        title = getattr(item, "title", None)
        if title and isinstance(title, str) and title.strip():
            return title.strip()
    except Exception:
        pass

    if index is not None:
        return f"item[{index}]"

    return "<unknown>"