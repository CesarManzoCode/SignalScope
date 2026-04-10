"""
Source selection utility.

Provides filtering logic to determine which sources are active
based on the current execution mode and include/exclude configuration.
"""

from __future__ import annotations

import logging
from typing import Any

from core.types.source import Source

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_MODE = "dev"
_VALID_MODES = {"dev", "security"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def select_sources(sources: list[Source], config: dict[str, Any]) -> list[Source]:
    """
    Filter and return the relevant sources based on the provided configuration.

    Selection logic (unchanged):
      1. If ``config.sources.include`` is non-empty, keep only those sources
         whose name is in the include list.
      2. Otherwise, keep sources whose category matches the current mode.
      3. After step 1 or 2, remove any source whose name appears in
         ``config.sources.exclude``.

    Args:
        sources: Full list of available :class:`Source` instances.
        config:  Runtime configuration dictionary. Expected keys:
                   - ``mode``    (str)  – execution environment.
                   - ``sources`` (dict) – sub-dict with optional ``include``
                                          and ``exclude`` lists of source names.

    Returns:
        Filtered list of :class:`Source` instances.  Returns an empty list
        (rather than raising) when inputs are valid but yield no matches.

    Raises:
        TypeError:  If ``sources`` is not a list or ``config`` is not a dict.
        ValueError: If ``config`` contains structurally invalid values.
    """
    # ------------------------------------------------------------------
    # 1. Input validation
    # ------------------------------------------------------------------
    _validate_inputs(sources, config)

    # ------------------------------------------------------------------
    # 2. Extract and sanitize configuration values
    # ------------------------------------------------------------------
    mode, include_list, exclude_list = _parse_config(config)

    if not sources:
        logger.warning("select_sources called with an empty sources list.")
        return []

    logger.debug(
        "select_sources | mode=%r | include=%r | exclude=%r | total_sources=%d",
        mode,
        include_list,
        exclude_list,
        len(sources),
    )

    # ------------------------------------------------------------------
    # 3. Primary filter  (include-list OR category match)
    # ------------------------------------------------------------------
    try:
        if include_list:
            filtered = _filter_by_include(sources, include_list)
        else:
            filtered = _filter_by_category(sources, mode)
    except Exception as exc:
        logger.exception(
            "Unexpected error during primary source filtering. "
            "mode=%r include=%r",
            mode,
            include_list,
        )
        raise RuntimeError("Primary source filtering failed.") from exc

    logger.debug("After primary filter: %d source(s) remain.", len(filtered))

    # ------------------------------------------------------------------
    # 4. Secondary filter  (exclude-list)
    # ------------------------------------------------------------------
    if exclude_list:
        try:
            filtered = _filter_by_exclude(filtered, exclude_list)
        except Exception as exc:
            logger.exception(
                "Unexpected error during exclude filtering. exclude=%r",
                exclude_list,
            )
            raise RuntimeError("Exclude source filtering failed.") from exc

        logger.debug("After exclude filter: %d source(s) remain.", len(filtered))

    # ------------------------------------------------------------------
    # 5. Warn when result is unexpectedly empty
    # ------------------------------------------------------------------
    if not filtered:
        logger.warning(
            "select_sources returned 0 sources. "
            "mode=%r | include=%r | exclude=%r | candidates=%d",
            mode,
            include_list,
            exclude_list,
            len(sources),
        )

    return filtered


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _validate_inputs(sources: Any, config: Any) -> None:
    """
    Validate that the top-level arguments have the expected types.

    Args:
        sources: Value passed as the sources' argument.
        config:  Value passed as the config argument.

    Raises:
        TypeError: If either argument has an unexpected type.
    """
    if not isinstance(sources, list):
        raise TypeError(
            f"'sources' must be a list, got {type(sources).__name__!r}."
        )
    if not isinstance(config, dict):
        raise TypeError(
            f"'config' must be a dict, got {type(config).__name__!r}."
        )

    # Validate individual source objects (fail fast with a clear message)
    for index, item in enumerate(sources):
        if not isinstance(item, Source):
            raise TypeError(
                f"sources[{index}] is not a Source instance "
                f"(got {type(item).__name__!r})."
            )


def _parse_config(config: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    """
    Extract, coerce, and validate the configuration values used for filtering.

    Args:
        config: Raw configuration dictionary.

    Returns:
        Tuple of (mode, include_list, exclude_list).

    Raises:
        ValueError: If any config value has an invalid type or structure.
    """
    # -- mode --
    raw_mode = config.get("mode")
    if raw_mode is None:
        logger.debug("'mode' not found in config; defaulting to %r.", _DEFAULT_MODE)
        mode = _DEFAULT_MODE
    elif not isinstance(raw_mode, str):
        raise ValueError(
            f"config['mode'] must be a string, got {type(raw_mode).__name__!r}."
        )
    else:
        mode = raw_mode.strip() or _DEFAULT_MODE
        if mode not in _VALID_MODES:
            logger.warning(
                "Unknown mode %r. Expected one of %s. Proceeding anyway.",
                mode,
                sorted(_VALID_MODES),
            )

    # -- sources sub-dict --
    raw_sources_cfg = config.get("sources")
    if raw_sources_cfg is None:
        sources_cfg: dict[str, Any] = {}
    elif not isinstance(raw_sources_cfg, dict):
        raise ValueError(
            f"config['sources'] must be a dict, "
            f"got {type(raw_sources_cfg).__name__!r}."
        )
    else:
        sources_cfg = raw_sources_cfg

    # -- include list --
    include_list = _extract_name_list(sources_cfg, "include")

    # -- exclude list --
    exclude_list = _extract_name_list(sources_cfg, "exclude")

    return mode, include_list, exclude_list


def _extract_name_list(sources_cfg: dict[str, Any], key: str) -> list[str]:
    """
    Extract and validate a list of source names from the sources sub-config.

    Args:
        sources_cfg: The ``config['sources']`` sub-dictionary.
        key:         Either ``"include"`` or ``"exclude"``.

    Returns:
        List of non-empty source name strings (maybe empty).

    Raises:
        ValueError: If the value is present but not a list, or if any
                    element is not a non-empty string.
    """
    raw = sources_cfg.get(key)

    if not raw:  # None, [], "", etc.
        return []

    if not isinstance(raw, list):
        raise ValueError(
            f"config['sources'][{key!r}] must be a list, "
            f"got {type(raw).__name__!r}."
        )

    validated: list[str] = []
    for index, item in enumerate(raw):
        if not isinstance(item, str):
            raise ValueError(
                f"config['sources'][{key!r}][{index}] must be a string, "
                f"got {type(item).__name__!r}."
            )
        stripped = item.strip()
        if not stripped:
            logger.warning(
                "config['sources']['%s'][%d] is an empty/whitespace string; skipping.",
                key,
                index,
            )
            continue
        validated.append(stripped)

    return validated


def _filter_by_include(sources: list[Source], include_list: list[str]) -> list[Source]:
    """
    Keep only sources whose name appears in *include_list*.

    Args:
        sources:      Full list of Source instances.
        include_list: Non-empty list of allowed source names.

    Returns:
        Filtered list of Source instances.
    """
    include_set = set(include_list)
    result = [s for s in sources if s.name in include_set]

    missing = include_set - {s.name for s in result}
    if missing:
        logger.warning(
            "The following names in 'include' did not match any source: %s",
            sorted(missing),
        )

    return result


def _filter_by_category(sources: list[Source], mode: str) -> list[Source]:
    """
    Keep only sources whose category matches *mode*.

    Args:
        sources: Full list of Source instances.
        mode:    Active execution mode (e.g. ``"dev"``, ``"prod"``).

    Returns:
        Filtered list of Source instances.
    """
    result = [s for s in sources if s.category == mode]

    if not result:
        logger.warning(
            "No sources match category %r. "
            "Available categories: %s",
            mode,
            sorted({s.category for s in sources}),
        )

    return result


def _filter_by_exclude(sources: list[Source], exclude_list: list[str]) -> list[Source]:
    """
    Remove sources whose name appears in *exclude_list*.

    Args:
        sources:      List of Source instances after the primary filter.
        exclude_list: Names of sources to drop.

    Returns:
        Filtered list of Source instances.
    """
    exclude_set = set(exclude_list)
    removed = [s.name for s in sources if s.name in exclude_set]

    if removed:
        logger.debug("Excluding source(s): %s", removed)

    return [s for s in sources if s.name not in exclude_set]