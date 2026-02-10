#!/usr/bin/env python3
"""Test Cyrillic output using python-escpos and textln.

Usage (from project root, with venv activated):

  python -m test.test_encoding
"""

from __future__ import annotations

from escpos import printer
from escpos.constants import CODEPAGE_CHANGE

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
        profile=config.PRINTER_PROFILE,
    )


def main() -> None:
    p = get_printer()

    # Initialize and select ESC/POS codepage ID from config (6 == cp1251 on your printer)
    p._raw(b"\x1b\x40")  # ESC @
    p._raw(CODEPAGE_CHANGE + bytes((config.CODEPAGE_ID,)))

    text = "Привет, мир!"

    p.set(align="left", font=config.FONT or "a")
    p.textln("=== escpos textln test ===")
    p.textln(text)
    p.textln("")

    try:
        p.cut()
    except TypeError:
        try:
            p.cut(mode="PART")
        except TypeError:
            p.cut()


if __name__ == "__main__":
    main()

