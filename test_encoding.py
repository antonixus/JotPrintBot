#!/usr/bin/env python3
"""Simple script to test printer output with different encodings.

This bypasses python-escpos and writes directly to the serial device,
just like:

  echo -e "Привет\n\n\n" | iconv -t cp1251 > /dev/serial0

Usage (from project root):

  python test_encoding.py
      → uses default text "Привет, мир!" and encodings [CODEPAGE, cp866, utf-8]

  python test_encoding.py "Привет, мир!" cp1251 cp866
      → prints the given text once per encoding
"""

from __future__ import annotations

import sys

import serial

import config


def get_serial() -> serial.Serial:
    """Create a raw serial connection using current config/.env settings."""
    return serial.Serial(
        port=config.SERIAL_PORT,
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
        encodings = argv[1:] or [config.CODEPAGE, "cp866", "utf-8"]
    else:
        text = "Привет, мир!"
        encodings = [config.CODEPAGE, "cp1251", "cp866"]

    ser = get_serial()

    # Header (ASCII only, safe under any 8-bit codepage)
    ser.write(b"=== Encoding test ===\n")
    ser.write(f"Text: {text}\n\n".encode("ascii", errors="replace"))

    for enc in encodings:
        ser.write(f"--- encoding: {enc} ---\n".encode("ascii", errors="replace"))
        try:
            data = text.encode(enc, errors="replace")
        except LookupError:
            ser.write(f"(codec {enc!r} not found)\n\n".encode("ascii", errors="replace"))
            continue

        # Write raw bytes, exactly like iconv > /dev/serial0
        ser.write(data + b"\n\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
