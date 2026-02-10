#!/usr/bin/env python3
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
        codepage=config.CODEPAGE,
    )


def main():

    p = get_printer()
    p.set(align="left", font=config.FONT or "a")
    p.textln("=== Encoding test ===")
    text = "Привет, мир! Hello, world!"
    data = text.decode('UTF-8').encode('cp1251', errors="replace")
    p.textln(f"Text: {data}")
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

