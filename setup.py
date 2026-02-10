#!/usr/bin/env python3
"""Setup script: create default config files, folders, and systemd service for production deploy."""

import argparse
import os
import subprocess
import sys
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
FONT=12x24
DENSITY_LEVEL=4
"""


def get_systemd_service_content(base: Path, user: str) -> str:
    """Generate systemd service file for bot.py in virtual environment."""
    base_str = str(base)
    return f"""[Unit]
Description=Telegram Printer Bot
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={base_str}
ExecStart={base_str}/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Setup Telegram Printer Bot for production")
    parser.add_argument(
        "--install-service",
        action="store_true",
        help="Install systemd service (requires sudo)",
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("SUDO_USER", os.environ.get("USER", "pi")),
        help="User to run the service (default: pi or current user)",
    )
    args = parser.parse_args()

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

    # Generate systemd service file
    service_content = get_systemd_service_content(base, args.user)
    service_path = base / "bot.service"
    service_path.write_text(service_content, encoding="utf-8")
    print(f"Generated systemd service: {service_path}")

    # Install service if requested
    if args.install_service:
        if sys.platform != "linux":
            print("Warning: systemd install is supported on Linux only.")
        else:
            try:
                subprocess.run(
                    ["sudo", "cp", str(service_path), "/etc/systemd/system/"],
                    check=True,
                )
                subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
                subprocess.run(["sudo", "systemctl", "enable", "bot"], check=True)
                print("Service installed and enabled. Start with: sudo systemctl start bot")
            except subprocess.CalledProcessError as e:
                print(f"Service installation failed: {e}", file=sys.stderr)
                sys.exit(1)
    else:
        print(
            "  → To install service on Raspberry Pi: "
            "python setup.py --install-service"
        )


if __name__ == "__main__":
    main()
