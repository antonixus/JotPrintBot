"""Async printer module for CSN-A2 TTL thermal printer (ESC/POS compatible)."""

import asyncio
import logging
from typing import Any, List, Union

import config
from formatter import PrintJob, QueueItem, Segment

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
            # Attempt to set printer media width (pixels and mm) if not specified in profile.
            try:
                media = self.printer.profile.media.get("width", {})
                pixels = media.get("pixels")
                mm = media.get("mm")
                if pixels in (None, "Unknown") and config.MEDIA_WIDTH_PIXELS:
                    self.printer.profile.media["width"]["pixels"] = config.MEDIA_WIDTH_PIXELS
                if mm in (None, "Unknown") and config.MEDIA_WIDTH_MM:
                    self.printer.profile.media["width"]["mm"] = config.MEDIA_WIDTH_MM
            except Exception as e:
                logger.debug(f"Could not set printer media width: {e}")

        # Queue can hold either plain strings or formatted jobs (list[Segment])
        self.queue: asyncio.Queue[QueueItem] = asyncio.Queue()
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

    async def print_qr(self, data: str, size: int = config.QR_SIZE) -> None:
        """Print QR code for the given data. Non-blocking.

        Size, centering and image implementation are controlled by config:
          - config.QR_SIZE: base module size (overridden by `size` arg)
          - config.QR_CENTER: whether to center the QR image
          - config.QR_IMG_IMPL: image impl: bitImageRaster / graphics / bitImageColumn
        """
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

    async def print_formatted(self, job: PrintJob) -> None:
        """Print a formatted job (list of segments) asynchronously."""

        if self._mock:
            preview = "".join(seg.text for seg in job)[:50]
            logger.info("Printed formatted (mock): %s", preview)
            return

        for attempt in range(3):
            try:
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    self._do_print_formatted,
                    job,
                )
                preview = "".join(seg.text for seg in job)[:50]
                logger.info("Printed formatted: %s", preview)
                return
            except Exception as e:
                logger.error("Formatted print attempt %d failed: %s", attempt + 1, e)
                if attempt == 2:
                    raise
                await asyncio.sleep(0.5)

    def _apply_segment_style(self, seg: Segment) -> None:
        """Apply ESC/POS style for a single segment."""

        style = seg.style
        set_kwargs: dict[str, Any] = {}

        if "bold" in style:
            set_kwargs["bold"] = bool(style["bold"])
        if "underline" in style:
            set_kwargs["underline"] = int(style["underline"])
        if "font" in style:
            set_kwargs["font"] = str(style["font"])

        if set_kwargs:
            try:
                self.printer.set(**set_kwargs)
            except Exception:
                # Some profiles may not support all kwargs
                pass

        # Double-strike for strikethrough.
        if style.get("double_strike"):
            try:
                # ESC G 1  -> enable double-strike
                self.printer._raw(b"\x1b\x47\x01")
            except Exception:
                pass

    def _reset_style(self) -> None:
        """Reset printer style to defaults from config."""

        try:
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
            # Not all printers/profile combinations support all options.
            pass

        # Always ensure double-strike is turned off after each segment.
        try:
            # ESC G 0  -> disable double-strike
            self.printer._raw(b"\x1b\x47\x00")
        except Exception:
            pass

    def _do_print_formatted(self, job: PrintJob) -> None:
        """Blocking formatted print (runs in executor)."""

        for seg in job:
            if not seg.text:
                continue
            self._apply_segment_style(seg)
            self.printer.text(seg.text)
            self._reset_style()

        self._cut()

    def _do_print_qr(self, data: str, size: int) -> None:
        """Blocking QR print (runs in executor)."""
        # Use software-rendered QR (native=False) to get proper UTF-8 encoding.
        # Image printing parameters are controlled via image_arguments according
        # to python-escpos docs (impl, center, high_density_*).
        image_arguments: dict[str, Any] = {
            "impl": config.QR_IMG_IMPL,
            "center": config.QR_CENTER,
            "high_density_vertical": True,
            "high_density_horizontal": True,
        } 
        
        try:
            self.printer.qr(
                data,
                native=False,
                size=size,
                image_arguments=image_arguments,
            )
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
            item: QueueItem = await self.queue.get()
            try:
                if isinstance(item, str):
                    await self.print_text(item)
                else:
                    await self.print_formatted(item)
            except Exception as e:
                if isinstance(item, str):
                    preview = item[:50]
                else:
                    preview = "".join(seg.text for seg in item)[:50]
                logger.error(
                    "Queue processing failed for job %r: %s", preview, e, exc_info=True
                )
            finally:
                self.queue.task_done()
