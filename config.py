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
CODEPAGE: str = os.getenv("CODEPAGE", "cp1251").strip()
FONT: str = os.getenv("FONT", "12x24").strip()
DENSITY_LEVEL: int = int(os.getenv("DENSITY_LEVEL", "4").strip())
