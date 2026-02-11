"""Standalone QR code printing test script for the ESC/POS thermal printer.

Usage examples (run from project root, with venv activated):

    python -m test.qr_print_test
    python -m test.qr_print_test "Привет"
    python -m test.qr_print_test "Привет мир" --qr-size 8 --impl graphics --center
    python -m test.qr_print_test "Привет" --impl bitImageColumn --no-high-density-horizontal

This script:
  - Connects to the printer using the same serial settings as `printer.AsyncPrinter`
  - Lets you choose the image printing implementation: bitImageRaster, graphics, bitImageColumn
  - Lets you choose QR code size (1–16)
  - Lets you control image_arguments: center, high_density_vertical, high_density_horizontal
  - Lets you override printer density (ESC/POS `set(density=...)`)
  - Uses UTF-8 / software-rendered QR (native=False) so Cyrillic text scans correctly
"""

from __future__ import annotations

import argparse
import logging

from escpos.printer import Serial  # type: ignore[import]

import config


logger = logging.getLogger(__name__)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print a test QR code with configurable image implementation and settings."
    )
    parser.add_argument(
        "content",
        nargs="?",
        default="Привет",
        help='Text to encode into the QR code (default: "Привет").',
    )
    parser.add_argument(
        "--qr-size",
        type=int,
        default=config.QR_SIZE,
        help="QR code module size (1–16, default from config.QR_SIZE).",
    )
    parser.add_argument(
        "--impl",
        choices=("bitImageRaster", "graphics", "bitImageColumn"),
        default="bitImageRaster",
        help="Image printing implementation for the QR (default: bitImageRaster).",
    )
    parser.add_argument(
        "--native",
        action="store_true",
        help=(
            "Use printer native QR mode (may break Cyrillic decoding on phones). "
            "Default is software-rendered (native=False) for correct UTF-8."
        ),
    )
    parser.add_argument(
        "--center",
        dest="center",
        action="store_true",
        help="Center the QR image.",
    )
    parser.add_argument(
        "--no-center",
        dest="center",
        action="store_false",
        help="Do not center the QR image (default).",
    )
    parser.set_defaults(center=False)

    parser.add_argument(
        "--high-density-vertical",
        dest="high_density_vertical",
        action="store_true",
        help="Print image in high vertical density (default).",
    )
    parser.add_argument(
        "--no-high-density-vertical",
        dest="high_density_vertical",
        action="store_false",
        help="Print image in low vertical density (stretched).",
    )
    parser.set_defaults(high_density_vertical=True)

    parser.add_argument(
        "--high-density-horizontal",
        dest="high_density_horizontal",
        action="store_true",
        help="Print image in high horizontal density (default).",
    )
    parser.add_argument(
        "--no-high-density-horizontal",
        dest="high_density_horizontal",
        action="store_false",
        help="Print image in low horizontal density (stretched).",
    )
    parser.set_defaults(high_density_horizontal=True)

    parser.add_argument(
        "--density",
        type=int,
        default=config.DENSITY_LEVEL,
        help="Printer density level passed to ESC/POS set(density=...).",
    )

    return parser


def create_printer() -> Serial:
    """Create and initialize a Serial printer using config settings."""
    printer = Serial(
        devfile=config.SERIAL_PORT,
        baudrate=config.BAUDRATE,
        bytesize=config.SERIAL_BYTESIZE,
        parity=config.SERIAL_PARITY,
        stopbits=config.SERIAL_STOPBITS,
        timeout=config.SERIAL_TIMEOUT,
        dsrdtr=config.SERIAL_DSRDTR,
        profile=config.PRINTER_PROFILE,
    )

    # Initialize and set code page (e.g. cp1251) like in `printer.AsyncPrinter`.
    printer._raw(b"\x1b\x40")  # ESC @ (initialize)
    printer._raw(b"\x1bt" + bytes((config.CODEPAGE_ID,)))  # ESC t <n> (codepage)

    return printer


def safe_cut(printer: Serial) -> None:
    """Cut paper with compatibility across python-escpos versions."""
    try:
        printer.cut(partial=True)
        return
    except TypeError:
        pass
    try:
        printer.cut(mode="PART")
        return
    except TypeError:
        pass
    try:
        printer.cut()
    except Exception:
        # Some printers/profiles may not support cutting; ignore.
        logger.exception("Failed to cut paper (ignoring).")


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logger.info(
        "Printing QR: content=%r, size=%d, impl=%s, native=%s, center=%s, "
        "high_density_vertical=%s, high_density_horizontal=%s, density=%d",
        args.content,
        args.qr_size,
        args.impl,
        args.native,
        args.center,
        args.high_density_vertical,
        args.high_density_horizontal,
        args.density,
    )

    printer = create_printer()

    # Set base text/print density options; align follows center flag.
    try:
        printer.set(
            underline=config.TEXT_UNDERLINE,
            align="center" if args.center else config.TEXT_ALIGN,
            font=config.FONT,
            width=config.TEXT_WIDTH,
            height=config.TEXT_HEIGHT,
            density=args.density,
            invert=config.TEXT_INVERT,
            smooth=config.TEXT_SMOOTH,
            flip=config.TEXT_FLIP,
        )
    except Exception:
        # Not all printers/profiles support all set() kwargs.
        logger.exception("printer.set() failed (continuing with defaults).")

    # Build image_arguments for qr(), as per python-escpos docs.
    image_arguments = {
        "center": args.center,
        "high_density_vertical": args.high_density_vertical,
        "high_density_horizontal": args.high_density_horizontal,
        "impl": args.impl,
    }

    try:
        # Use native flag as requested; note that for Cyrillic + smartphone decoding,
        # native=False is usually required so the QR is rendered as a UTF-8 image.
        printer.qr(
            args.content,
            size=args.qr_size,
            native=args.native,
            image_arguments=image_arguments,
        )
    except TypeError:
        # Older python-escpos versions might not support image_arguments/native.
        logger.exception(
            "printer.qr() does not support image_arguments/native; trying fallback call."
        )
        printer.qr(args.content, size=args.qr_size)

    safe_cut(printer)


if __name__ == "__main__":
    main()

