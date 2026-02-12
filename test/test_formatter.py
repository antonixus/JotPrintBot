"""Tests for formatter module that maps Telegram entities to print segments."""

from unittest.mock import MagicMock

import pytest
from aiogram.types import Message, MessageEntity

from formatter import build_print_job, message_to_queue_item, Segment


def test_build_print_job_basic_styles():
    text = "Hello world"
    entities = [
        MessageEntity(type="bold", offset=0, length=5),
        MessageEntity(type="code", offset=6, length=5),
    ]

    job = build_print_job(text, entities)

    # Expect at least two styled segments: "Hello" bold, "world" font='b'
    bold_seg = next(seg for seg in job if seg.text.strip() == "Hello")
    code_seg = next(seg for seg in job if seg.text.strip() == "world")

    assert bold_seg.style.get("bold") is True
    assert code_seg.style.get("font") == "b"


def test_message_to_queue_item_no_entities_returns_stripped():
    msg = MagicMock(spec=Message)
    msg.text = "  Hello  "
    msg.caption = None
    # Do not define .entities / .caption_entities on purpose (MagicMock default)

    item = message_to_queue_item(msg)

    assert isinstance(item, str)
    assert item == "Hello"


@pytest.mark.parametrize(
    "etype, key, expected",
    [
        ("bold", "bold", True),
        ("underline", "underline", 1),
        ("strikethrough", "double_strike", True),
        ("code", "font", "b"),
        ("pre", "font", "b"),
        ("blockquote", "bold", True),
    ],
)
def test_entity_type_to_style_mapping(etype, key, expected):
    text = "X"
    entities = [MessageEntity(type=etype, offset=0, length=1)]
    job = build_print_job(text, entities)
    assert len(job) == 1
    seg: Segment = job[0]
    assert seg.text == "X"
    assert seg.style.get(key) == expected

