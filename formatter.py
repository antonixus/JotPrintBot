"""Helpers to convert Telegram message entities into printer-friendly segments.

This module parses Telegram entities (bold, underline, strikethrough, code/pre,
blockquote) and maps them to ESC/POS style dictionaries suitable for use with
python-escpos' ``set()``.

Italic is intentionally **not** implemented – italic entities are ignored.
Monospaced/code/pre is rendered using printer font ``'b'`` (Font B).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple, Union

from aiogram.types import Message, MessageEntity


@dataclass(frozen=True)
class Segment:
    """Single printable segment with ESC/POS style."""

    text: str
    style: Dict[str, Any]


PrintJob = List[Segment]
QueueItem = Union[str, PrintJob]


def _utf16_range_to_py_slice(text: str, offset: int, length: int) -> tuple[int, int]:
    """Convert Telegram UTF-16 code unit range to Python slice indices.

    Telegram MessageEntity.offset / length are in UTF-16 code units.
    Python strings are indexed by Unicode code points, so we need a mapping.
    """

    if not text:
        return 0, 0

    # Build mapping from character index -> starting UTF-16 code unit index.
    char_to_cu: List[int] = []
    cu_index = 0
    for ch in text:
        char_to_cu.append(cu_index)
        # Number of UTF-16 code units for this character.
        cu_index += len(ch.encode("utf-16-le")) // 2

    total_cu = cu_index
    start_cu = max(0, min(offset, total_cu))
    end_cu = max(start_cu, min(offset + length, total_cu))

    def cu_to_char_index(target: int) -> int:
        # Find first char whose starting CU index >= target.
        for i, cu in enumerate(char_to_cu):
            if cu >= target:
                return i
        return len(text)

    start_idx = cu_to_char_index(start_cu)
    end_idx = cu_to_char_index(end_cu)
    return start_idx, end_idx


def _extract_entities(
    text: str, entities: Sequence[MessageEntity]
) -> List[Tuple[int, int, str]]:
    """Return list of (start_index, end_index, entity_type) in Python indices."""

    result: List[Tuple[int, int, str]] = []
    for ent in entities:
        try:
            ent_type = str(ent.type)
            start, end = _utf16_range_to_py_slice(text, ent.offset, ent.length)
            if start < end:
                result.append((start, end, ent_type))
        except Exception:
            # Ignore malformed entities
            continue
    return result


def build_print_job(text: str, entities: Sequence[MessageEntity]) -> PrintJob:
    """Build a list of segments (text + style) from text and entities.

    - Bold         → style["bold"] = True
    - Underline    → style["underline"] = 1
    - Strikethrough→ style["invert"] = True
    - Code / Pre   → style["font"] = "b"
    - Blockquote   → style["double_height"] = True and style["double_width"] = True
    - Italic       → ignored
    """

    if not text:
        return []

    norm_entities = _extract_entities(text, entities)
    if not norm_entities:
        return [Segment(text=text, style={})]

    # Build all boundaries.
    boundaries = {0, len(text)}
    for start, end, _ in norm_entities:
        boundaries.add(start)
        boundaries.add(end)
    ordered = sorted(boundaries)

    segments: PrintJob = []
    for i in range(len(ordered) - 1):
        seg_start = ordered[i]
        seg_end = ordered[i + 1]
        if seg_start >= seg_end:
            continue
        seg_text = text[seg_start:seg_end]
        if not seg_text:
            continue

        # Collect all entities covering this entire subrange.
        active_types = {
            etype
            for (start, end, etype) in norm_entities
            if start <= seg_start and end >= seg_end
        }

        style: Dict[str, Any] = {}

        if "bold" in active_types:
            style["bold"] = True

        if "underline" in active_types:
            style["underline"] = 1

        if "strikethrough" in active_types:
            style["invert"] = True

        if "code" in active_types or "pre" in active_types:
            style["font"] = "b"

        if "blockquote" in active_types:
            style["double_height"] = True
            style["double_width"] = True

        # Italic is intentionally ignored.

        segments.append(Segment(text=seg_text, style=style))

    return segments


def message_to_queue_item(message: Message) -> QueueItem:
    """Convert aiogram Message to either plain string or formatted PrintJob.

    - If there are no usable entities → return stripped text (backward compatible).
    - If there are entities          → return a list[Segment].
    """

    text = (message.text or message.caption or "") or ""

    # Safely extract entities from Message; account for MagicMocks in tests.
    raw_entities = getattr(message, "entities", None)
    if not isinstance(raw_entities, (list, tuple)):
        raw_entities = getattr(message, "caption_entities", None)
    if not isinstance(raw_entities, (list, tuple)):
        raw_entities = []

    entities: Sequence[MessageEntity] = raw_entities  # type: ignore[assignment]

    if not entities:
        # Preserve previous behavior: trim leading/trailing whitespace.
        return text.strip()

    return build_print_job(text, entities)

