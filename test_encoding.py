#!/usr/bin/env python3
"""Simple script to test printer output with different encodings.

Usage (from project root, venv activated):

  python test_encoding.py
      → uses a default sample text and encodings

  python test_encoding.py "Привет, мир!" cp1251 cp866
      → prints the given text once per encoding

For each encoding, the script:
  - prints the encoding name
  - prints the text encoded with that codec
"""

from __future__ import annotations

import sys

from escpos import printer

import config


def get_printer() -> printer.Serial:
    """Create a Serial printer using current config/.env settings."""
    return printer.Serial(
        devfile=config.SERIAL_PORT,
        baudrate=config.BAUDRATE,
        bytesize=config.SERIAL_BYTESIZE,
        parity=config.SERIAL_PARITY,
        stopbits=config.SERIAL_STOPBITS,
        timeout=config.SERIAL_TIMEOUT,
        dsrdtr=config.SERIAL_DSRDTR,
    )


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]

    # First argument: text; rest: encodings
    if argv:
        text = argv[0]
        encodings = argv[1:] or [config.CODEPAGE, "cp866", "latin-1"]
    else:
        text = "Привет, мир! Hello, world!"
        encodings = [config.CODEPAGE, "cp866", "latin-1"]

    p = get_printer()

    p.set(align="left", font=config.FONT or "a")
    p.textln("=== Encoding test ===")
    p.textln(f"Text: {text}")
    p.textln("")

    for enc in encodings:
        p.textln(f"--- encoding: {enc} ---")
        try:
            data = text.encode(enc, errors="replace")
        except LookupError:
            p.textln(f"(codec {enc!r} not found)\n")
            continue

        # Use latin-1 trick so bytes go 1:1 over the wire
        pseudo_str = data.decode("latin-1")
        p.textln(pseudo_str)
        p.textln("")

    try:
        p.cut()
    except TypeError:
        try:
            p.cut(mode="PART")
        except TypeError:
            p.cut()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

