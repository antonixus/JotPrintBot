"""Print task model: optional header + payload for printer queue.

Used to ensure every print (text/formatted/QR) can optionally be prefixed with
the same header (timestamp + @username + horizontal rule + blank line).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from formatter import PrintJob


@dataclass(frozen=True)
class HeaderInfo:
    timestamp: str
    user: str


@dataclass(frozen=True)
class TextPayload:
    content: str | PrintJob


@dataclass(frozen=True)
class QrPayload:
    data: str


@dataclass(frozen=True)
class ImagePayload:
    image_path: str


@dataclass(frozen=True)
class PrintTask:
    header: HeaderInfo | None
    payload: Union[TextPayload, QrPayload, ImagePayload]

