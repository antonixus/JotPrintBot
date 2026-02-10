#!/usr/bin/env python3
"""Print ESC/POS code page tables on the thermal printer.

Usage examples (from project root, with venv activated):

  python codepage_tables.py
      → prints the default "USA" table.

  python codepage_tables.py cp1251
      → prints the table for the named code page (if supported by python-escpos).

  python codepage_tables.py 17
      → prints the table for numeric codepage ID 17.

The serial connection parameters and device are taken from config.py / .env.
"""

from __future__ import annotations

import sys

from escpos import printer
from escpos.constants import (
    CODEPAGE_CHANGE,
    CTL_CR,
    CTL_FF,
    CTL_HT,
    CTL_LF,
    CTL_VT,
    ESC,
)

import config


def get_printer() -> printer.Serial:
    """Create a Serial printer using the same settings as the bot."""
    return printer.Serial(
        devfile=config.SERIAL_PORT,
        baudrate=config.BAUDRATE,
        bytesize=config.SERIAL_BYTESIZE,
        parity=config.SERIAL_PARITY,
        stopbits=config.SERIAL_STOPBITS,
        timeout=config.SERIAL_TIMEOUT,
        dsrdtr=config.SERIAL_DSRDTR,
    )


def print_codepage(p: printer.Serial, codepage: str) -> None:
    """Print a single code page table."""
    # Select codepage by numeric ID or symbolic name
    if codepage.isdigit():
        cp_id = int(codepage)
        p._raw(CODEPAGE_CHANGE + bytes((cp_id,)))
    else:
        # This uses python-escpos' charcode mapping; valid names depend on library version.
        p.charcode(codepage)

    sep = ""

    # Table header (top row)
    p.set(font="b")
    header = "  " + sep.join(hex(s)[2:] for s in range(0, 16))
    p._raw(header + "\n")
    p.set()  # reset to defaults

    # Table body
    for x in range(0, 16):
        # First column
        p.set(font="b")
        p._raw(f"{hex(x)[2:]} ")
        p.set()

        for y in range(0, 16):
            byte = bytes((x * 16 + y,))

            # Avoid sending control characters directly
            if byte in (ESC, CTL_LF, CTL_FF, CTL_CR, CTL_HT, CTL_VT):
                ch: bytes | str = " "
            else:
                ch = byte

            p._raw(ch)
            p._raw(sep)
        p._raw("\n")


def main(argv: list[str] | None = None) -> None:
    """Init printer and print codepage tables."""
    argv = argv if argv is not None else sys.argv[1:]
    codes = argv or ["USA"]

    p = get_printer()

    # Small header
    p.set(height=2, width=2, align="center")
    p._raw("Code page tables\n\n")
    p.set()

    for cp in codes:
        p.set(height=2, width=2)
        p._raw(f"{cp}\n\n")
        print_codepage(p, cp)
        p._raw("\n\n")

    # Final cut
    try:
        p.cut()
    except TypeError:
        # Older/newer escpos versions may have different cut() signatures
        try:
            p.cut(mode="PART")
        except TypeError:
            p.cut()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

