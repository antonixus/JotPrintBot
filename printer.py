"""Async printer module for CSN-A2 TTL thermal printer (ESC/POS compatible)."""

import asyncio
import logging
from typing import Any

import config

logger = logging.getLogger(__name__)


class MockPrinter:
    """Stub printer for testing without hardware."""

    def text(self, data: str | bytes) -> None:
        """No-op stub."""

    def textln(self, data: str | bytes) -> None:
        """No-op stub for line-oriented text."""

    def cut(self, partial: bool = True) -> None:
        """No-op stub."""

    def set(self, **kwargs: Any) -> None:
        """No-op stub for python-escpos set()."""

    def status(self) -> bool:
        """Return online status."""
        return True

    def is_online(self) -> bool:
        """Return online status (python-escpos compatible)."""
        return True

    def paper_status(self) -> int:
        """Return paper status (python-escpos compatible)."""
        return 2

    def charcode(self, code: str) -> None:
        """No-op stub."""

    def _raw(self, data: bytes) -> None:
        """No-op stub."""

    def qr(self, data: str, native: bool = True, size: int = 8) -> None:
        """No-op stub for QR codes."""


class AsyncPrinter:
    """Async wrapper for CSN-A2 TTL thermal printer using python-escpos."""

    def __init__(self) -> None:
        self.printer: Any
        if config.MOCK_PRINTER:
            self.printer = MockPrinter()
        else:
            # Import lazily so dev/tests can run without escpos installed
            from escpos.printer import Serial  # type: ignore

            # Serial settings based on common ESC/POS UART defaults:
            # 9600 baud, 8N1, with DSR/DTR flow control enabled.
            # See: https://circuitdigest.com/microcontroller-projects/thermal-printer-interfacing-with-raspberry-pi-zero-to-print-text-images-and-bar-codes
            self.printer = Serial(
                devfile=config.SERIAL_PORT,
                baudrate=config.BAUDRATE,
                bytesize=config.SERIAL_BYTESIZE,
                parity=config.SERIAL_PARITY,
                stopbits=config.SERIAL_STOPBITS,
                timeout=config.SERIAL_TIMEOUT,
                dsrdtr=config.SERIAL_DSRDTR,
                profile=config.PRINTER_PROFILE,
            )
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self._mock = config.MOCK_PRINTER

        try:
            # Initialize and select ESC/POS code page once at startup.
            # ESC @ (initialize)
            self.printer._raw(b"\x1b\x40")
            # ESC t <n>  (select codepage ID; on your printer 6 == cp1251)
            self.printer._raw(b"\x1bt" + bytes((config.CODEPAGE_ID,)))

            # Basic text style defaults (best-effort; depends on printer profile)
            # FONT is passed directly to python-escpos (usually "a" or "b")
            font = config.FONT or "a"
            self.printer.set(
                underline=config.TEXT_UNDERLINE,
                align=config.TEXT_ALIGN,
                font=font,
                width=config.TEXT_WIDTH,
                height=config.TEXT_HEIGHT,
                density=config.DENSITY_LEVEL,
                invert=config.TEXT_INVERT,
                smooth=config.TEXT_SMOOTH,
                flip=config.TEXT_FLIP,
            )
        except Exception:
            # Not all backends/printers support all settings
            pass

    async def print_text(self, text: str) -> None:
        if self._mock:
            logger.info("Printed (mock): %s", text[:50])
            return
        for attempt in range(3):
            try:
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    self._do_print,
                    text,
                )
                logger.info("Printed: %s", text[:50])
                return
            except Exception as e:
                logger.error("Print attempt %d failed: %s", attempt + 1, e)
                if attempt == 2:
                    raise
                await asyncio.sleep(0.5)

    async def print_qr(self, data: str, size: int = config.QR_SIZE,qralign: str = config.QR_ALIGN) -> None:
        """Print QR code for the given data. Non-blocking."""
        if self._mock:
            logger.info("QR printed (mock): %s", data[:50])
            return
        for attempt in range(3):
            try:
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    self._do_print_qr,
                    data,
                    size,
                    qralign,
                )
                logger.info("QR printed: %s", data[:50])
                return
            except Exception as e:
                logger.error("QR print attempt %d failed: %s", attempt + 1, e)
                if attempt == 2:
                    raise
                await asyncio.sleep(0.5)

    def _do_print(self, text: str) -> None:
        """Blocking print (runs in executor)."""

        self.printer.textln(text)
        self._cut()

    def _do_print_qr(self, data: str, size: int, qralign: str) -> None:
        """Blocking QR print (runs in executor)."""
        self.printer.set(align=qralign)
        # Use software-rendered QR (native=False) to get proper UTF-8 encoding
        # See: https://python-escpos.readthedocs.io/en/latest/user/cli-user.html#qr
        try:
            self.printer.qr(data, native=False, size=size)
        except TypeError:
            # Fallback for older versions without `native` kwarg
            self.printer.qr(data, size=size)
        self._cut()

    def _cut(self) -> None:
        """Cut paper with python-escpos version compatibility."""
        # python-escpos API differs across versions:
        # - some accept cut(partial=True)
        # - some accept cut(mode="PART")
        # - some accept cut() only
        try:
            self.printer.cut(partial=True)
            return
        except TypeError:
            pass
        try:
            self.printer.cut(mode="PART")
            return
        except TypeError:
            pass
        self.printer.cut()

    def _query_status_sync(self) -> dict[str, object]:
        """Query printer status synchronously (runs in executor)."""
        online = bool(self.printer.is_online())
        paper: int | None
        try:
            paper = int(self.printer.paper_status())
        except Exception:
            paper = None
        return {"online": online, "paper": paper}

    async def status(self) -> dict[str, object]:
        """Return printer online + paper status."""
        if self._mock:
            return {"online": True, "paper": 2}
        try:
            return await asyncio.get_running_loop().run_in_executor(
                None, self._query_status_sync
            )
        except Exception as e:
            logger.error("Status check failed: %s", e, exc_info=True)
            return {"online": False, "paper": None}

    async def _process_queue(self) -> None:
        """Process print queue continuously."""
        while True:
            text = await self.queue.get()
            try:
                await self.print_text(text)
            except Exception as e:
                logger.error(
                    "Queue processing failed for text %r: %s", text[:50], e, exc_info=True
                )
            finally:
                self.queue.task_done()
