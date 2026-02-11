#!/usr/bin/env python3

from __future__ import annotations

from escpos import printer
from escpos.constants import CODEPAGE_CHANGE

def get_printer() -> printer.Serial:
    """Create a Serial printer using current config/.env settings."""
    return printer.Serial(
        devfile="/dev/serial0",
        baudrate=9600,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=1.0,
        dsrdtr=True,
        profile="RP326",
    )

def main() -> None:
    p = get_printer()

    # Initialize and select ESC/POS codepage ID from config (6 == cp1251 on your printer)
    p._raw(b"\x1b\x40")  # ESC @
    p._raw(CODEPAGE_CHANGE + bytes((6,)))

    p.set(align="left", font="a")
    p.text("12345678901234567890123456789012   <-- 32 chars\n")
    p.textln("")
    p.textln("Should be 32 chars max in Font A")
    p.cut()

    p.set(align="left", font="b")
    p.text("123456789012345678901234567890123456789012   <-- try 42\n")
    p.textln("Should fit ~42 chars in Font B")
    p.cut()

if __name__ == "__main__":
    main()





