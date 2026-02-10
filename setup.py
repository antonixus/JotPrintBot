#!/usr/bin/env python3
"""Setup script: create default config files and folders for production deploy."""

from pathlib import Path

# Folders
DIRS = ["logs"]

# Default .env template (placeholders, safe for first-run)
ENV_TEMPLATE = """# Telegram Printer Bot - Production Config
# Replace placeholders before running

BOT_TOKEN=YOUR_BOT_TOKEN_FROM_BOTFATHER
ADMIN_ID=YOUR_TELEGRAM_USER_ID
SERIAL_PORT=/dev/serial0
BAUDRATE=9600
WHITELIST=YOUR_TELEGRAM_USER_ID
MOCK_PRINTER=false
CODEPAGE=cp1251
FONT=12x24
DENSITY_LEVEL=4
"""


def main() -> None:
    base = Path(__file__).resolve().parent

    # Create folders
    for name in DIRS:
        path = base / name
        path.mkdir(exist_ok=True)
        print(f"Created directory: {path}")

    # Create .env if missing
    env_path = base / ".env"
    if env_path.exists():
        print(f"Config already exists: {env_path}")
    else:
        env_path.write_text(ENV_TEMPLATE, encoding="utf-8")
        print(f"Created config: {env_path}")
        print("  → Edit .env and set BOT_TOKEN, ADMIN_ID, WHITELIST before running.")


if __name__ == "__main__":
    main()
