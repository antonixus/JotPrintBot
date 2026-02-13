"""Configuration module - loads settings from .env file."""

import logging
import os

from dotenv import load_dotenv

# Must load .env before reading any variables
if not load_dotenv():
    raise ValueError(".env file not found")

logger = logging.getLogger(__name__)


def _get_required(key: str) -> str:
    """Get required env var; log warning and raise if missing."""
    value = os.getenv(key)
    if not value or not value.strip():
        logger.warning("Missing or empty required key in .env: %s", key)
        raise ValueError(f"Missing required environment variable: {key}")
    return value.strip()


def _parse_whitelist(value: str | None) -> list[int]:
    """Parse comma-separated string of integers into list[int].
    Handles both '1,2,3' and '[1,2,3]' formats.
    """
    if not value or not value.strip():
        return []
    raw = value.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def _parse_bool(value: str | None) -> bool:
    """Parse string to bool; default False for missing/invalid."""
    if not value:
        return False
    return value.strip().lower() in ("true", "1", "yes", "on")


# Required
BOT_TOKEN: str = _get_required("BOT_TOKEN")
ADMIN_ID: int = int(_get_required("ADMIN_ID"))

# Optional with defaults
SERIAL_PORT: str = os.getenv("SERIAL_PORT", "/dev/serial0").strip()
BAUDRATE: int = int(os.getenv("BAUDRATE", "9600").strip())
WHITELIST: list[int] = _parse_whitelist(os.getenv("WHITELIST"))
MOCK_PRINTER: bool = _parse_bool(os.getenv("MOCK_PRINTER", "false"))
# Printer font as used by python-escpos (typically "a" or "b")
FONT: str = os.getenv("FONT", "a").strip()
DENSITY_LEVEL: int = int(os.getenv("DENSITY_LEVEL", "4").strip())
# Python codec name for text encoding (for Cyrillic use "cp1251")
CODEPAGE: str = os.getenv("CODEPAGE", "cp1251").strip()
# ESC/POS code page ID used with ESC t (on your printer 6 == cp1251)
CODEPAGE_ID: int = int(os.getenv("CODEPAGE_ID", "6").strip())
# Printer profile name for python-escpos (e.g. "RP326")
PRINTER_PROFILE: str = os.getenv("PRINTER_PROFILE", "RP326").strip()
# Printer media width in pixels
MEDIA_WIDTH_PIXELS: int = int(os.getenv("MEDIA_WIDTH_PIXELS").strip())
# Printer media width in mm
MEDIA_WIDTH_MM: float = float(os.getenv("MEDIA_WIDTH_PIXELS").strip())

# Default text style for python-escpos .set()
TEXT_UNDERLINE: int = int(os.getenv("TEXT_UNDERLINE", "0").strip())
TEXT_ALIGN: str = os.getenv("TEXT_ALIGN", "left").strip()
TEXT_WIDTH: int = int(os.getenv("TEXT_WIDTH", "1").strip())
TEXT_HEIGHT: int = int(os.getenv("TEXT_HEIGHT", "1").strip())
TEXT_INVERT: int = int(os.getenv("TEXT_INVERT", "0").strip())
TEXT_SMOOTH: bool = _parse_bool(os.getenv("TEXT_SMOOTH", "false"))
TEXT_FLIP: bool = _parse_bool(os.getenv("TEXT_FLIP", "false"))

# Bot behavior
PRINT_RATE_LIMIT_SECONDS: int = int(os.getenv("PRINT_RATE_LIMIT_SECONDS", "10").strip())
# Enable/disable Telegram entity-based formatting → ESC/POS styles
PRINT_TELEGRAM_FORMATTING: bool = _parse_bool(
    os.getenv("PRINT_TELEGRAM_FORMATTING", "true")
)

# Per-message header printing (timestamp + @username + rule line)
PRINT_HEADER_ENABLED: bool = _parse_bool(os.getenv("PRINT_HEADER_ENABLED", "true"))
# Header horizontal line width (characters); should match your printer/font width
HEADER_LINE_WIDTH: int = int(os.getenv("HEADER_LINE_WIDTH", "42").strip())
# QR code settings
QR_SIZE: int = int(os.getenv("QR_SIZE", "3").strip())
QR_ALIGN: str = os.getenv("QR_ALIGN", "center").strip()
QR_DENSITY: int = int(os.getenv("QR_DENSITY", "3").strip())
QR_CENTER: bool = _parse_bool(os.getenv("QR_CENTER", "false"))
QR_IMG_IMPL: str = os.getenv("QR_IMG_IMPL", "bitImageColumn").strip()

# Serial line settings for python-escpos Serial printer (optional)
SERIAL_BYTESIZE: int = int(os.getenv("SERIAL_BYTESIZE", "8").strip())
SERIAL_PARITY: str = os.getenv("SERIAL_PARITY", "N").strip().upper()
SERIAL_STOPBITS: int = int(os.getenv("SERIAL_STOPBITS", "1").strip())
SERIAL_TIMEOUT: float = float(os.getenv("SERIAL_TIMEOUT", "1.0").strip())
SERIAL_DSRDTR: bool = _parse_bool(os.getenv("SERIAL_DSRDTR", "true"))
