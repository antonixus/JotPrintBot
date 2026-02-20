"""Async printer module for CSN-A2 TTL thermal printer (ESC/POS compatible)."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, List, Union

import config
from formatter import PrintJob, Segment
from print_tasks import HeaderInfo, PrintTask, QrPayload, TextPayload, ImagePayload

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

    def image(self, img_source: Any, **kwargs: Any) -> None:
        """No-op stub for image printing."""
        # Log enhancement info for testing
        from PIL import Image
        if isinstance(img_source, Image.Image):
            logger.debug("Mock image print: mode=%s, size=%s", img_source.mode, img_source.size)


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

        # Queue holds PrintTask objects (optional header + payload)
        self.queue: asyncio.Queue[PrintTask] = asyncio.Queue()
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

    def _print_header(self, header: HeaderInfo) -> None:
        """Print per-message header (font B), then reset styles."""

        width = int(getattr(config, "HEADER_LINE_WIDTH", 42))

        try:
            self.printer.set(font="b")
        except Exception:
            pass

        line1 = f"{header.timestamp} {header.user}"[:width]
        self.printer.textln(line1)
        self.printer.textln("-" * width)
        self.printer.textln("")

        self._reset_style()

    def _do_print_task(self, task: PrintTask) -> None:
        """Blocking task print (runs in executor)."""

        if task.header is not None:
            self._print_header(task.header)

        payload = task.payload
        if isinstance(payload, TextPayload):
            content = payload.content
            if isinstance(content, str):
                self.printer.textln(content)
            else:
                for seg in content:
                    if not seg.text:
                        continue
                    self._apply_segment_style(seg)
                    self.printer.text(seg.text)
                    self._reset_style()
        elif isinstance(payload, QrPayload):
            # QrPayload
            data = payload.data
            size = config.QR_SIZE
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
                self.printer.qr(data, size=size)
            # Re-initialize after QR (uses image mode when native=False)
            self._reinitialize_printer()
        elif isinstance(payload, ImagePayload):
            # ImagePayload
            self._do_print_image(payload.image_path)
        else:
            raise ValueError(f"Unknown payload type: {type(payload)}")

        self._cut()

    async def print_task(self, task: PrintTask) -> None:
        """Print a PrintTask (optional header + payload) asynchronously."""

        if self._mock:
            preview: str
            if isinstance(task.payload, QrPayload):
                preview = f"QR:{task.payload.data[:40]}"
            elif isinstance(task.payload, ImagePayload):
                preview = f"Image:{task.payload.image_path}"
                # Delete temp file in mock mode too
                try:
                    Path(task.payload.image_path).unlink(missing_ok=True)
                except Exception as e:
                    logger.warning("Failed to delete temp image file in mock: %s", e)
            elif isinstance(task.payload.content, str):
                preview = task.payload.content[:40]
            else:
                preview = "".join(seg.text for seg in task.payload.content)[:40]
            logger.info("Printed task (mock): %s", preview)
            return

        for attempt in range(3):
            try:
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    self._do_print_task,
                    task,
                )
                return
            except Exception as e:
                logger.error("Task print attempt %d failed: %s", attempt + 1, e)
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
        if "double_height" in style:
            set_kwargs["double_height"] = bool(style["double_height"])
        if "double_width" in style:
            set_kwargs["double_width"] = bool(style["double_width"])
        if "invert" in style:
            set_kwargs["invert"] = bool(style["invert"])

        if set_kwargs:
            try:
                self.printer.set(**set_kwargs)
            except Exception:
                # Some profiles may not support all kwargs
                pass

    def _reinitialize_printer(self) -> None:
        """Send ESC/POS initialize sequence to clear graphics mode and reset printer state.

        Use after image/QR printing; some printers (e.g. CSN-A2) stay in graphics mode
        until ESC @ (Initialize) is sent, causing garbled text until power cycle.
        """
        if self._mock:
            return
        try:
            # ESC @ — Initialize: clears buffer, resets all modes (like power-on)
            self.printer._raw(b"\x1b\x40")
            # ESC t <n> — Select code page (e.g. 6 = cp1251 for Cyrillic)
            self.printer._raw(b"\x1bt" + bytes((config.CODEPAGE_ID,)))
            self._reset_style()
        except Exception as e:
            logger.warning("Printer re-initialize failed: %s", e)

    def _reset_style(self) -> None:
        """Reset printer style to defaults from config."""

        try:
            font = config.FONT or "a"
            self.printer.set(
                underline=config.TEXT_UNDERLINE,
                align=config.TEXT_ALIGN,
                font=font,
                bold=False,
                width=config.TEXT_WIDTH,
                height=config.TEXT_HEIGHT,
                density=config.DENSITY_LEVEL,
                invert=config.TEXT_INVERT,
                smooth=config.TEXT_SMOOTH,
                flip=config.TEXT_FLIP,
                double_height=False,
                double_width=False,
            )
        except Exception:
            # Not all printers/profile combinations support all options.
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

    def _do_print_image(self, image_path: str) -> None:
        """Blocking image print (runs in executor).

        Opens image with PIL, handles orientation (rotate landscape 90° CW),
        resizes to printer width (384 dots for CSN-A2), optionally applies
        image enhancements, sets density, and prints. Deletes the temp file
        after printing (or on error).
        """
        from PIL import Image

        try:
            # Open and convert to RGB (CSN-A2 is B&W but PIL handles conversion)
            img = Image.open(image_path).convert("RGB")

            # Rotate landscape images 90° clockwise (PIL rotate is CCW, so -90 = CW)
            if img.width > img.height:
                img = img.rotate(-90, expand=True)

            # Resize to printer width while preserving aspect ratio.
            # Do this before enhancement so dithering works on final-resolution pixels.
            target_width = getattr(config, "IMAGE_PRINT_WIDTH", 384)
            if img.width != target_width:
                ratio = target_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)

            # Apply image enhancements for thermal printer output, if enabled.
            if config.IMAGE_ENHANCE_ENABLED:
                logger.debug(
                    "Applying image enhancement for thermal printer output "
                    "(contrast=%s, sharpness=%s, brightness=%s, grayscale=%s, dithering=%s)",
                    config.IMAGE_CONTRAST,
                    config.IMAGE_SHARPNESS,
                    config.IMAGE_BRIGHTNESS,
                    config.IMAGE_GRAYSCALE,
                    config.IMAGE_DITHERING,
                )
                img = self._enhance_image(img)

            # Set print density before printing
            self.printer.set(density=config.IMAGE_DENSITY)

            # Print image with configured parameters
            self.printer.image(
                img,
                impl=config.IMAGE_IMPL,
                fragment_height=config.IMAGE_FRAGMENT_HEIGHT,
                center=config.IMAGE_CENTER,
                high_density_vertical=True,
                high_density_horizontal=True,
            )

            # Full re-initialize after image: ESC @ clears graphics mode so next text prints correctly
            self._reinitialize_printer()
        finally:
            # Always delete temp file, even on error
            try:
                Path(image_path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning("Failed to delete temp image file %s: %s", image_path, e)

    def _enhance_image(self, img: Any) -> Any:
        """Apply image enhancements for thermal printer compatibility.

        Args:
            img: PIL Image object (RGB mode)

        Returns:
            Enhanced PIL Image ready for ESC/POS printing
        """
        from PIL import ImageEnhance, ImageFilter, Image

        # Step 1: Convert to grayscale for thermal printer compatibility
        if config.IMAGE_GRAYSCALE:
            img = img.convert("L")

        # Step 2: Apply contrast enhancement
        if config.IMAGE_CONTRAST != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(config.IMAGE_CONTRAST)

        # Step 3: Apply sharpness enhancement
        if config.IMAGE_SHARPNESS != 1.0:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(config.IMAGE_SHARPNESS)

        # Step 4: Apply brightness adjustment
        if config.IMAGE_BRIGHTNESS != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(config.IMAGE_BRIGHTNESS)

        # Step 5: Apply dithering for smooth gradients (Floyd-Steinberg)
        if config.IMAGE_DITHERING:
            img = img.convert("1", dither=Image.FLOYDSTEINBERG)

        return img

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
            task: PrintTask = await self.queue.get()
            try:
                await self.print_task(task)
            except Exception as e:
                logger.error("Queue processing failed for task %r: %s", task, e, exc_info=True)
            finally:
                self.queue.task_done()
