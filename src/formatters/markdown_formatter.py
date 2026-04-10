"""
Markdown report generator for FinalItem collections.

This module transforms collections of ``FinalItem`` objects into well-formatted
Markdown reports and persists them to disk. It is designed following
production-grade robustness principles: defensive input validation,
exhaustive error handling, structured logging, atomic disk writes, and
isolation of failures by individual item (a corrupted item should not
bring down the entire report).

Architecture:
    - Domain layer: ``FinalItem`` (imported from ``core.types``).
    - Infrastructure layer: this module, responsible for Markdown serialization
      and persistence to the file system.

Guarantees:
    - Atomic writes: the final file never ends up in a partial state.
    - Deterministic naming: timestamp with microsecond resolution
      to avoid collisions in concurrent executions.
    - Fail-soft per item: individual formatting errors are logged and
      replaced with a placeholder, preserving the rest of the report.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Final, Iterable, List, Optional

from core.types.final_item import FinalItem

# ---------------------------------------------------------------------------
# Module-level configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# Project root, resolved absolutely to avoid ambiguities
# when the module is imported from different working directories.
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent.parent

# Output directory where Markdown reports are written.
OUTPUT_DIR: Final[Path] = BASE_DIR / "output"

# Visual separator between item sections in the final report.
SECTION_SEPARATOR: Final[str] = "\n\n---\n\n"

# Timestamp format for file names. Includes microseconds to
# guarantee uniqueness even under concurrent executions in the same second.
TIMESTAMP_FORMAT: Final[str] = "%Y-%m-%d_%H-%M-%S-%f"

# Placeholder used when an individual item fails to format.
# Allows preserving the integrity of the overall report (fail-soft).
ITEM_ERROR_PLACEHOLDER: Final[str] = (
    "# [Formatting Error]\n\n"
    "> An error occurred while formatting this item. "
    "See application logs for details."
)

#: Pattern to sanitize problematic characters in file names.
_UNSAFE_FILENAME_CHARS: Final[re.Pattern[str]] = re.compile(r"[^\w\-.]")


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class MarkdownExportError(Exception):
    """Base exception for any failure in Markdown export."""


class OutputDirectoryError(MarkdownExportError):
    """Raised when the output directory cannot be created or written to."""


class ReportWriteError(MarkdownExportError):
    """Raised when writing the report to disk fails."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def save_as_markdown(
    items: Iterable[FinalItem],
    *,
    output_dir: Optional[Path] = None,
) -> Path:
    """
    Serializes a collection of :class:`FinalItem` objects as a Markdown report
    and persists it atomically to disk.

    The function is defensive at all trust boundaries:

    1. Validates that ``items`` is iterable and not empty.
    2. Guarantees the existence and write permissions of the destination directory.
    3. Isolates formatting failures by individual item (fail-soft).
    4. Writes the file atomically using a temporary file and
       ``os.replace``, avoiding partially written reports in case of
       interruption.

    Args:
        items: Iterable of ``FinalItem`` objects to serialize. Is materialized
            internally as a list to allow prior validation and multiple
            safe passes.
        output_dir: Alternative output directory. If ``None``, the
            default :data:`OUTPUT_DIR` is used. Useful for testing and for
            consumers that need custom paths.

    Returns:
        Absolute path of the generated Markdown file.

    Raises:
        TypeError: If ``items`` is not iterable.
        ValueError: If the item collection is empty after materialization.
        OutputDirectoryError: If the output directory cannot be created
            or is not writable.
        ReportWriteError: If the atomic write of the report fails.
    """
    # --- 1. Input validation -----------------------------------------------
    try:
        materialized_items: List[FinalItem] = list(items)
    except TypeError as exc:
        logger.error("save_as_markdown received a non-iterable 'items' argument.")
        raise TypeError(
            "'items' must be an iterable of FinalItem instances."
        ) from exc

    if not materialized_items:
        logger.warning("save_as_markdown called with an empty item collection.")
        raise ValueError("Cannot generate a report from an empty item collection.")

    logger.debug(
        "Starting Markdown export for %d item(s).", len(materialized_items)
    )

    # --- 2. Output directory preparation --------------------------------
    target_dir: Path = (output_dir or OUTPUT_DIR).resolve()
    _ensure_output_directory(target_dir)

    # --- 3. File path resolution ----------------------------------------
    file_path: Path = _build_report_path(target_dir)
    logger.debug("Resolved report file path: %s", file_path)

    # --- 4. Section formatting (fail-soft per item) --------------------
    sections: List[str] = []
    failed_items: int = 0

    for index, item in enumerate(materialized_items):

        # noinspection PyBroadException
        try:
            sections.append(format_item(item))

        except Exception:
            failed_items += 1
            logger.exception(
                "Failed to format item at index %d; substituting placeholder.",
                index,
            )
            sections.append(ITEM_ERROR_PLACEHOLDER)

    if failed_items:
        logger.warning(
            "Markdown export completed with %d/%d item(s) failing to format.",
            failed_items,
            len(materialized_items),
        )

    full_text: str = SECTION_SEPARATOR.join(sections)

    # --- 5. Atomic disk write ------------------------------------------
    _atomic_write_text(file_path, full_text)

    logger.info(
        "Markdown report successfully written to %s (%d item(s), %d failure(s)).",
        file_path,
        len(materialized_items),
        failed_items,
    )
    return file_path


# ---------------------------------------------------------------------------
# Formatting logic
# ---------------------------------------------------------------------------


def format_item(item: FinalItem) -> str:
    """
    Converts a single :class:`FinalItem` to its Markdown representation.

    The formatting is tolerant to missing or ``None`` attributes: only
    sections for which the item has meaningful content are emitted. Values
    are normalized to strings with ``str()`` to absorb unexpected types
    without breaking serialization.

    Args:
        item: ``FinalItem`` object to format. Must expose at least the
            ``title`` attribute; the rest are optional.

    Returns:
        Markdown representation of the item as a single string.

    Raises:
        TypeError: If ``item`` is ``None``.
        AttributeError: If ``item`` does not expose the mandatory ``title`` attribute.
    """
    if item is None:
        raise TypeError("format_item received a None item.")

    # ``title`` is the only strictly required field; we fail fast
    # if it is missing so that the caller can apply its fail-soft policy.
    title = getattr(item, "title", None)
    if not title:
        raise AttributeError(
            "FinalItem is missing the mandatory 'title' attribute."
        )

    parts: List[str] = [f"# {title}"]

    # --- Summary ---------------------------------------------------------------
    summary = getattr(item, "summary", None)
    if summary:
        parts.append("## Summary")
        parts.append(str(summary))

    # --- Key Points --------------------------------------------------------
    key_points = getattr(item, "key_points", None)
    if key_points:
        parts.append("## Key Points")
        if isinstance(key_points, Iterable):
            for point in key_points:
                if point is None:
                    continue
                parts.append(f"- {point}")

    # --- Details ---------------------------------------------------------------
    details = getattr(item, "details", None)
    if details:
        parts.append("## Details")
        parts.append(str(details))

    # --- Metadata: Source ------------------------------------------------------
    url = getattr(item, "url", None)
    if url:
        parts.append(f"\n**Source:** {url}")

    # --- Metadata: Priority ------------------------------------------------
    priority = getattr(item, "priority", None)
    if priority:
        parts.append(f"\n**Priority:** {priority}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _ensure_output_directory(directory: Path) -> None:
    """
    Guarantees that ``directory`` exists and is writable by the current process.

    Creates the full hierarchy if necessary (``parents=True``) and explicitly
    verifies write permissions with ``os.access`` to fail early with an
    actionable message, rather than exploding later during report write.

    Args:
        directory: Path of the directory to prepare.

    Raises:
        OutputDirectoryError: If the directory cannot be created, if the path
            exists but is not a directory, or if it is not writable.
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as exc:
        logger.error("Failed to create output directory %s: %s", directory, exc)
        raise OutputDirectoryError(
            f"Cannot create output directory {directory!s}: {exc}"
        ) from exc

    if not directory.is_dir():
        raise OutputDirectoryError(
            f"Output path {directory!s} exists but is not a directory."
        )

    if not os.access(directory, os.W_OK):
        raise OutputDirectoryError(
            f"Output directory {directory!s} is not writable by the current process."
        )


def _build_report_path(directory: Path) -> Path:
    """
    Builds the report file path with a unique timestamp.

    The name is sanitized to remove any characters that could be
    problematic on heterogeneous file systems (Windows/Linux/macOS).

    Args:
        directory: Parent directory where the file will be located.

    Returns:
        Absolute path of the new Markdown file (not yet created).
    """
    timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    safe_timestamp = _UNSAFE_FILENAME_CHARS.sub("_", timestamp)
    return directory / f"report_{safe_timestamp}.md"


def _atomic_write_text(file_path: Path, content: str) -> None:
    """
    Writes ``content`` to ``file_path`` atomically.

    Strategy: first write to a temporary file within the same destination
    directory (to guarantee that ``os.replace`` is an atomic file system
    operation) and then rename. If any step fails, the temporary file is
    deleted and the final file never ends up in a partially written state.

    Args:
        file_path: Final destination path of the file.
        content: UTF-8 text content to write.

    Raises:
        ReportWriteError: If the write or atomic rename fails.
    """
    temp_path: Optional[Path] = None
    try:
        # ``delete=False`` because we want to manually control the lifecycle:
        # the file must survive the ``close()`` to be able to rename it.
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=file_path.parent,
            prefix=f".{file_path.stem}_",
            suffix=".tmp",
            delete=False,
        ) as tmp_file:
            temp_path = Path(tmp_file.name)
            tmp_file.write(content)
            # flush + fsync guarantee that data is on disk before the
            # rename, protecting against operating system crashes.
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

        # ``os.replace`` is atomic on POSIX and Windows (since Python 3.3).
        assert temp_path is not None
        os.replace(temp_path, file_path)
        temp_path = None  # The temporary file no longer exists; we avoid cleaning it up below.

    except (OSError, UnicodeEncodeError) as exc:
        logger.error(
            "Atomic write failed for %s: %s", file_path, exc, exc_info=True
        )
        raise ReportWriteError(
            f"Failed to write Markdown report to {file_path!s}: {exc}"
        ) from exc

    finally:
        # Defensive cleanup: if something failed between temporary file creation and
        # the rename, we ensure not to leave garbage in the output directory.
        if temp_path is not None and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError as cleanup_exc:
                logger.warning(
                    "Failed to clean up temporary file %s: %s",
                    temp_path,
                    cleanup_exc,
                )