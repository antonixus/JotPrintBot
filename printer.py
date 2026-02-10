"""Async printer module for CSN-A2 TTL thermal printer (ESC/POS compatible)."""

import asyncio
import logging
import textwrap

import config
from escpos.printer import Serial

logger = logging.getLogger(__name__)


class MockPrinter:
    """Stub printer for testing without hardware."""

    def text(self, data: str | bytes) -> None:
        """No-op stub."""

    def cut(self, partial: bool = True) -> None:
        """No-op stub."""

    def status(self) -> bool:
        """Return online status."""
        return True

    def charcode(self, code: str) -> None:
        """No-op stub."""

    def _raw(self, data: bytes) -> None:
        """No-op stub."""


class AsyncPrinter:
    """Async wrapper for CSN-A2 TTL thermal printer using python-escpos."""

    def __init__(self) -> None:
        if config.MOCK_PRINTER:
            self.printer = MockPrinter()
        else:
            self.printer = Serial(
                devfile=config.SERIAL_PORT,
                baudrate=config.BAUDRATE,
                profile="TM-T88II",
            )
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self._mock = config.MOCK_PRINTER

        # Configure printer
        self.printer.charcode(config.CODEPAGE)
        if config.FONT == "12x24":
            # ESC M 0 = Font A (12x24)
            self.printer._raw(b"\x1b\x4d\x00")
        self.printer._raw(bytes([0x1D, 0x21, config.DENSITY_LEVEL]))

    async def print_text(self, text: str) -> None:
        """Print text with wrapping. Non-blocking."""
        wrapped = textwrap.fill(text, width=32)
        if self._mock:
            logger.info("Printed (mock): %s", text[:50])
            return
        for attempt in range(3):
            try:
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    self._do_print,
                    wrapped,
                )
                logger.info("Printed: %s", text[:50])
                return
            except Exception as e:
                logger.error("Print attempt %d failed: %s", attempt + 1, e)
                if attempt == 2:
                    raise
                await asyncio.sleep(0.5)

    def _do_print(self, wrapped: str) -> None:
        """Blocking print (runs in executor)."""
        self.printer.text(wrapped.encode(config.CODEPAGE))
        self.printer.cut(partial=True)

    async def status(self) -> dict[str, bool]:
        """Return printer online status."""
        if self._mock:
            return {"online": True}
        try:
            st = await asyncio.get_running_loop().run_in_executor(
                None, self.printer.status
            )
            return {"online": bool(st)}
        except Exception as e:
            logger.error("Status check failed: %s", e, exc_info=True)
            return {"online": False}

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
