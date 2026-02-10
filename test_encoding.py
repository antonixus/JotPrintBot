#!/usr/bin/env python3
"""Test Cyrillic output using python-escpos and textln."""

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
        profile="RP326",
    )


def main() -> None:
    p = get_printer()

    # Initialize and select ESC/POS codepage 6 (cp1251 on your printer)
    p._raw(b"\x1b\x40")  # ESC @
    p._raw(CODEPAGE_CHANGE + bytes((6,)))

    text = "Привет, мир!"

    # Encode text to cp1251, then map bytes 1:1 via latin-1 so that
    # python-escpos.textln sends exactly those bytes while still
    # accepting a Python str.

    p.set(align="left", font=config.FONT or "a")
    p.textln("=== escpos textln cp1251 test ===")
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