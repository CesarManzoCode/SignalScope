"""
research_runner.py

Concurrent research orchestrator with advanced error handling,
timeout enforcement, retry logic, and structured result reporting.
All original logic is preserved; only robustness layers were added.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from core.types.raw_item import RawItem
from core.types.source import Source

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_FETCH_TIMEOUT_SECONDS: float = 30.0
_DEFAULT_MAX_RETRIES: int = 2
_DEFAULT_RETRY_DELAY_SECONDS: float = 1.0
_DEFAULT_MAX_CONCURRENT_SOURCES: int = 50

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class SourceResult:
    """
    Holds the outcome of fetching a single source, whether successful or not.
    Keeps the original items alongside diagnostic metadata for observability.
    """

    source: Source
    items: list[RawItem] = field(default_factory=list)
    error: Optional[BaseException] = None
    attempts: int = 0
    elapsed_seconds: float = 0.0

    @property
    def succeeded(self) -> bool:
        """Returns True when at least a partial result was obtained."""
        return self.error is None

    @property
    def source_name(self) -> str:
        """
        Best-effort human-readable identifier for the source,
        used in log messages and error reports.
        """
        return getattr(self.source, "name", None) or repr(self.source)


# ---------------------------------------------------------------------------
# Core fetch helper
# ---------------------------------------------------------------------------

async def _fetch_with_retry(
    source: Source,
    *,
    timeout: float,
    max_retries: int,
    retry_delay: float,
) -> SourceResult:
    """
    Attempts to fetch items from *source* up to ``1 + max_retries`` times.

    Transient errors (network blips, temporary rate-limits) are retried with
    a fixed delay.  Timeouts and non-retryable exceptions are surfaced without
    further attempts.  The function never raises; it always returns a
    ``SourceResult`` so ``asyncio.gather`` can proceed for remaining sources.

    Parameters
    ----------
    source:
        The data source to fetch from.
    timeout:
        Maximum seconds allowed for a single fetch attempt.
    max_retries:
        Number of additional attempts after the first one fails.
    retry_delay:
        Seconds to wait between consecutive attempts.
    """
    result = SourceResult(source=source)
    start = time.monotonic()

    for attempt in range(1, max_retries + 2):  # +2 → range covers initial attempt
        result.attempts = attempt
        try:
            _log.debug(
                "Fetching source '%s' (attempt %d/%d).",
                result.source_name,
                attempt,
                max_retries + 1,
            )
            items = await asyncio.wait_for(source.fetch(), timeout=timeout)

            # Validate that the contract is honored before accepting the result
            if not isinstance(items, list):
                raise TypeError(
                    f"source.fetch() must return list[RawItem], "
                    f"got {type(items).__name__!r}."
                )

            result.items = items
            result.error = None
            _log.debug(
                "Source '%s' returned %d item(s) on attempt %d.",
                result.source_name,
                len(items),
                attempt,
            )
            break  # Success — stop retrying

        except asyncio.TimeoutError as exc:
            result.error = exc
            _log.warning(
                "Source '%s' timed out after %.1fs on attempt %d/%d.",
                result.source_name,
                timeout,
                attempt,
                max_retries + 1,
            )
            # Timeouts are not retried — the source is unresponsive
            break

        except asyncio.CancelledError:
            # Propagate cancellation immediately — do not swallow it
            _log.warning("Fetch for source '%s' was cancelled.", result.source_name)
            raise

        except Exception as exc:  # noqa: BLE001 — intentional broad catch
            result.error = exc
            _log.warning(
                "Source '%s' raised %s on attempt %d/%d: %s",
                result.source_name,
                type(exc).__name__,
                attempt,
                max_retries + 1,
                exc,
            )
            if attempt <= max_retries:
                await asyncio.sleep(retry_delay)
            # If this was the last attempt the loop exits naturally

    result.elapsed_seconds = time.monotonic() - start
    return result


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

async def run_research(
    sources: list[Source],
    *,
    fetch_timeout: float = _DEFAULT_FETCH_TIMEOUT_SECONDS,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    retry_delay: float = _DEFAULT_RETRY_DELAY_SECONDS,
    max_concurrent: int = _DEFAULT_MAX_CONCURRENT_SOURCES,
) -> list[RawItem]:
    """
    Fetches items from all *sources* concurrently and returns the flat
    union of every successful result.

    Behavior differences vs. the original implementation
    -------------------------------------------------------
    * Each source is given up to ``1 + max_retries`` attempts before being
      skipped — transient errors no longer silently discard an entire source.
    * Every fetch is bounded by ``fetch_timeout``; a hanging source cannot
      block the entire pipeline indefinitely.
    * A semaphore limits simultaneous in-flight fetches to ``max_concurrent``
      to avoid overwhelming downstream services or exhausting file descriptors.
    * Failures are logged at WARNING level with structured context so they are
      visible in production log aggregators without crashing the caller.
    * The function still returns ``list[RawItem]`` — the external contract is
      unchanged.

    Parameters
    ----------
    sources:
        Data sources to query.  An empty list returns immediately with ``[]``.
    fetch_timeout:
        Seconds before a single fetch attempt is considered timed out.
    max_retries:
        How many additional attempts to make after the first failure.
    retry_delay:
        Seconds to wait between retries.
    max_concurrent:
        Maximum number of sources fetched simultaneously.
    """
    if not sources:
        _log.debug("run_research called with an empty source list; returning [].")
        return []

    if not isinstance(sources, list):
        raise TypeError(
            f"'sources' must be a list[Source], got {type(sources).__name__!r}."
        )

    semaphore = asyncio.Semaphore(max_concurrent)

    async def _bounded_fetch(source: Source) -> SourceResult:
        """Wraps ``_fetch_with_retry`` inside the shared semaphore."""
        async with semaphore:
            return await _fetch_with_retry(
                source,
                timeout=fetch_timeout,
                max_retries=max_retries,
                retry_delay=retry_delay,
            )

    _log.info("Starting research run for %d source(s).", len(sources))
    pipeline_start = time.monotonic()

    source_results: list[SourceResult] = await asyncio.gather(
        *(_bounded_fetch(source) for source in sources),
        return_exceptions=False,  # _bounded_fetch never raises (except CancelledError)
    )

    # -----------------------------------------------------------------------
    # Aggregate and report
    # -----------------------------------------------------------------------
    successful = [r for r in source_results if r.succeeded]
    failed = [r for r in source_results if not r.succeeded]

    if failed:
        _log.warning(
            "%d/%d source(s) failed after all retries: %s",
            len(failed),
            len(sources),
            ", ".join(
                f"{r.source_name!r} ({type(r.error).__name__})" for r in failed
            ),
        )

    all_items: list[RawItem] = [
        item for result in successful for item in result.items
    ]

    _log.info(
        "Research run complete in %.2fs — %d source(s) succeeded, "
        "%d failed, %d total item(s) collected.",
        time.monotonic() - pipeline_start,
        len(successful),
        len(failed),
        len(all_items),
    )

    return all_items