#!/usr/bin/env python3
"""Test Cyrillic output by sending raw cp1251 bytes to the printer.

Equivalent to:
  echo -e "Привет\n\n\n" | iconv -t cp1251 > /dev/serial0
"""

from __future__ import annotations

import serial
import config


def main() -> None:
    # Open the same serial device the printer is on
    ser = serial.Serial(
        port=config.SERIAL_PORT,
        baudrate=config.BAUDRATE,
        bytesize=config.SERIAL_BYTESIZE,
        parity=config.SERIAL_PARITY,
        stopbits=config.SERIAL_STOPBITS,
        timeout=config.SERIAL_TIMEOUT,
        dsrdtr=config.SERIAL_DSRDTR,
    )

    # ESC/POS init + select codepage 6 (cp1251 on your printer)
    # ESC @ (initialize)
    ser.write(b"\x1b\x40")
    # ESC t 6  (select codepage ID 6)
    ser.write(b"\x1bt\x06")

    text = "Привет, мир!"
    ser.write(text.encode("cp1251") + b"\n\n\n")


if __name__ == "__main__":
    main()