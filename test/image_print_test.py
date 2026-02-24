"""Standalone image printing test script for the ESC/POS thermal printer.

Usage examples (run from project root, with venv activated):

    python -m test.image_print_test path/to/image.jpg
    python -m test.image_print_test path/to/image.jpg --impl graphics --center --print-width 384
    python -m test.image_print_test path/to/image.jpg --no-enhance
    python -m test.image_print_test path/to/image.jpg --contrast 1.8 --sharpness 2.5 --brightness 0.95
    python -m test.image_print_test path/to/image.jpg --double-width --double-height --print-config

Notes:
  - Uses the same config / serial settings as the bot (config.py / .env).
  - Uses AsyncPrinter._do_print_image(), so the temp image file is deleted after printing.
  - To avoid deleting your original input file, this script copies it to a temporary file first.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import tempfile
from pathlib import Path

import config
from printer import AsyncPrinter

logger = logging.getLogger(__name__)


def _add_bool_flag(
    parser: argparse.ArgumentParser,
    name: str,
    default: bool,
    help_true: str,
    help_false: str,
) -> None:
    parser.add_argument(f"--{name}", dest=name.replace("-", "_"), action="store_true", help=help_true)
    parser.add_argument(
        f"--no-{name}",
        dest=name.replace("-", "_"),
        action="store_false",
        help=help_false,
    )
    parser.set_defaults(**{name.replace("-", "_"): default})


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Print a test image with configurable ESC/POS image parameters and enhancement settings."
    )

    parser.add_argument(
        "image_path",
        help="Path to input image file (will be copied to a temp file before printing).",
    )

    parser.add_argument(
        "--impl",
        choices=("bitImageRaster", "graphics", "bitImageColumn"),
        default=config.IMAGE_IMPL,
        help="ESC/POS image implementation (default from config.IMAGE_IMPL).",
    )
    parser.add_argument(
        "--fragment-height",
        type=int,
        default=config.IMAGE_FRAGMENT_HEIGHT,
        help="Max fragment height for large images (default from config.IMAGE_FRAGMENT_HEIGHT).",
    )
    _add_bool_flag(
        parser,
        name="center",
        default=config.IMAGE_CENTER,
        help_true="Center the printed image.",
        help_false="Do not center the printed image.",
    )
    parser.add_argument(
        "--image-density",
        type=int,
        default=config.IMAGE_DENSITY,
        help="Density passed to set(density=...) before printing the image (default from config.IMAGE_DENSITY).",
    )
    parser.add_argument(
        "--print-width",
        type=int,
        default=config.IMAGE_PRINT_WIDTH,
        help="Target image width in pixels before printing (default from config.IMAGE_PRINT_WIDTH).",
    )

    _add_bool_flag(
        parser,
        name="enhance-enabled",
        default=config.IMAGE_ENHANCE_ENABLED,
        help_true="Enable image enhancement (default).",
        help_false="Disable image enhancement.",
    )
    parser.add_argument(
        "--contrast",
        type=float,
        default=config.IMAGE_CONTRAST,
        help="Contrast enhancement factor (default from config.IMAGE_CONTRAST).",
    )
    parser.add_argument(
        "--sharpness",
        type=float,
        default=config.IMAGE_SHARPNESS,
        help="Sharpness enhancement factor (default from config.IMAGE_SHARPNESS).",
    )
    parser.add_argument(
        "--brightness",
        type=float,
        default=config.IMAGE_BRIGHTNESS,
        help="Brightness adjustment factor (default from config.IMAGE_BRIGHTNESS).",
    )
    _add_bool_flag(
        parser,
        name="grayscale",
        default=config.IMAGE_GRAYSCALE,
        help_true="Convert to grayscale before printing (default).",
        help_false="Do not convert to grayscale.",
    )
    _add_bool_flag(
        parser,
        name="dithering",
        default=config.IMAGE_DITHERING,
        help_true="Apply Floyd-Steinberg dithering (default).",
        help_false="Disable dithering.",
    )

    _add_bool_flag(
        parser,
        name="high-density-vertical",
        default=True,
        help_true="Print image in high vertical density (default).",
        help_false="Print image in low vertical density.",
    )
    _add_bool_flag(
        parser,
        name="high-density-horizontal",
        default=True,
        help_true="Print image in high horizontal density (default).",
        help_false="Print image in low horizontal density.",
    )
    _add_bool_flag(
        parser,
        name="print-config",
        default=False,
        help_true="Print a header showing all effective image parameters before the image.",
        help_false="Do not print the configuration header (default).",
    )

    _add_bool_flag(
        parser,
        name="cut",
        default=True,
        help_true="Cut paper after printing (default).",
        help_false="Do not cut paper after printing.",
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force MOCK_PRINTER=true for this run (useful for smoke-testing without hardware).",
    )

    return parser


def apply_overrides(args: argparse.Namespace) -> None:
    """Apply CLI overrides by mutating the config module."""
    if args.mock:
        config.MOCK_PRINTER = True

    config.IMAGE_IMPL = args.impl
    config.IMAGE_FRAGMENT_HEIGHT = int(args.fragment_height)
    config.IMAGE_CENTER = bool(args.center)
    config.IMAGE_DENSITY = int(args.image_density)
    config.IMAGE_PRINT_WIDTH = int(args.print_width)

    config.IMAGE_ENHANCE_ENABLED = bool(getattr(args, "enhance_enabled"))
    config.IMAGE_CONTRAST = float(args.contrast)
    config.IMAGE_SHARPNESS = float(args.sharpness)
    config.IMAGE_BRIGHTNESS = float(args.brightness)
    config.IMAGE_GRAYSCALE = bool(args.grayscale)
    config.IMAGE_DITHERING = bool(args.dithering)
    config.IMAGE_HIGH_DENSITY_VERTICAL = bool(args.high_density_vertical)
    config.IMAGE_HIGH_DENSITY_HORIZONTAL = bool(args.high_density_horizontal)


def _copy_to_temp(input_path: Path) -> str:
    suffix = input_path.suffix if input_path.suffix else ".jpg"
    with tempfile.NamedTemporaryFile(prefix="jotprint_img_", suffix=suffix, delete=False) as f:
        temp_path = f.name
    shutil.copyfile(str(input_path), temp_path)
    return temp_path


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = build_arg_parser()
    args = parser.parse_args()

    input_path = Path(args.image_path).expanduser()
    if not input_path.exists():
        raise SystemExit(f"Input image does not exist: {input_path}")

    apply_overrides(args)

    logger.info(
        "Image settings: impl=%s fragment_height=%s center=%s density=%s print_width=%s",
        config.IMAGE_IMPL,
        config.IMAGE_FRAGMENT_HEIGHT,
        config.IMAGE_CENTER,
        config.IMAGE_DENSITY,
        config.IMAGE_PRINT_WIDTH,
    )
    logger.info(
        "Enhancement: enabled=%s contrast=%s sharpness=%s brightness=%s grayscale=%s dithering=%s",
        config.IMAGE_ENHANCE_ENABLED,
        config.IMAGE_CONTRAST,
        config.IMAGE_SHARPNESS,
        config.IMAGE_BRIGHTNESS,
        config.IMAGE_GRAYSCALE,
        config.IMAGE_DITHERING,
    )

    p = AsyncPrinter()

    if bool(getattr(args, "print_config")):
        # Print a configuration header before the image so it is easy to
        # correlate printed output with exact parameters.
        try:
            p.printer.textln("IMAGE CONFIG")
            p.printer.textln(f"impl={config.IMAGE_IMPL} frag_h={config.IMAGE_FRAGMENT_HEIGHT}")
            p.printer.textln(
                f"center={int(config.IMAGE_CENTER)} dens={config.IMAGE_DENSITY} width={config.IMAGE_PRINT_WIDTH}"
            )
            p.printer.textln(
                "enh={e} c={c} s={s} b={b}".format(
                    e=int(config.IMAGE_ENHANCE_ENABLED),
                    c=config.IMAGE_CONTRAST,
                    s=config.IMAGE_SHARPNESS,
                    b=config.IMAGE_BRIGHTNESS,
                )
            )
            p.printer.textln(
                "gray={g} dither={d}".format(
                    g=int(config.IMAGE_GRAYSCALE),
                    d=int(config.IMAGE_DITHERING),
                )
            )
            p.printer.textln(
                "hd_v={v} hd_h={h}".format(
                    v=int(getattr(args, "high_density_vertical")),
                    h=int(getattr(args, "high_density_horizontal")),
                )
            )
            p.printer.textln("")  # blank line before image
        except Exception as e:
            logger.warning("Failed to print config header: %s", e)

    temp_image_path = _copy_to_temp(input_path)
    logger.info("Printing temp copy: %s", temp_image_path)

    try:
        p._do_print_image(temp_image_path)
    finally:
        # _do_print_image deletes the file, but keep this as a safety net.
        Path(temp_image_path).unlink(missing_ok=True)

    if bool(getattr(args, "cut")):
        try:
            p._cut()
        except Exception as e:
            logger.warning("Failed to cut paper: %s", e)

    logger.info("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

