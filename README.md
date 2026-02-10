# Telegram Printer Bot

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://github.com/antonixus/telegram-printer-bot/blob/main/LICENSE)

## Introduction

**Telegram Printer Bot** is an asynchronous Python application that allows you to print text from Telegram messages to a thermal receipt printer. Send a message to the bot, and it will be printed on paper via a connected ESC/POS thermal printer.

**Supported hardware:**
- **CSN-A2 TTL** thermal printer (and other ESC/POS compatible models)
- **Raspberry Pi** / **DietPi** (serial connection via `/dev/serial0` or similar)
- Any Linux system with a serial or USB-Serial thermal printer

The bot uses [aiogram](https://docs.aiogram.dev/) for Telegram integration and [python-escpos](https://python-escpos.readthedocs.io/) for printer control.

---

## Functionality

- **Print text** — Send any text message (up to 1000 characters); it will be wrapped to 32 characters per line and queued for printing
- **Whitelist access** — Only users in the whitelist can use the bot; others receive "Access denied"
- **Rate limiting** — 1 print per 20 seconds per user by default (configurable)
- **Commands:**
  - `/start` — Welcome message and usage instructions
  - `/status` — Check if the printer is online
  - `/help` — List commands and limits
- **Mock mode** — Run without a physical printer for development (`MOCK_PRINTER=true`)
- **Error handling** — Exceptions are logged and the admin is notified via Telegram

---

## Installation and Configuration

### Requirements

- Python 3.8+ (3.12 recommended)
- Serial thermal printer (or mock mode for testing)

On Raspberry Pi / Debian you also need some system libraries for Pillow and Tk:

```bash
sudo apt update
sudo apt install -y \
  libtiff6 libjpeg-dev zlib1g-dev libfreetype6-dev \
  liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python3-tk
```

### 1. Clone the repository

```bash
git clone https://github.com/antonixus/telegram-printer-bot.git
cd telegram-printer-bot
```

### 2. Create virtual environment and install dependencies

```bash
python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Run setup (creates config, folders, and systemd service)

```bash
python setup.py
```

Setup creates the `logs/` folder, `.env` (if missing), and generates `bot.service` for systemd. On Raspberry Pi, install the service with:

```bash
python setup.py --install-service
```

### 4. Configure `.env`

Edit `.env` in the project root:

| Variable       | Required | Description                                      |
|----------------|----------|--------------------------------------------------|
| `BOT_TOKEN`    | Yes      | Telegram bot token from [@BotFather](https://t.me/BotFather) |
| `ADMIN_ID`     | Yes      | Your Telegram user ID (for error notifications)  |
| `WHITELIST`    | Yes      | Comma-separated Telegram user IDs allowed to use the bot |
| `SERIAL_PORT`  | No       | Serial device (default: `/dev/serial0`)          |
| `BAUDRATE`     | No       | Baud rate (default: `9600`)                      |
| `MOCK_PRINTER` | No       | `true` to run without hardware (default: `false`) |
| `FONT`         | No       | Printer font code for python-escpos (default: `a`) |
| `DENSITY_LEVEL`| No       | Print density 0–8 (default: `4`)                 |
| `PRINT_RATE_LIMIT_SECONDS` | No | Seconds between prints per user (default: `20`) |
| `CODEPAGE`     | No       | Text encoding used when sending bytes to the printer (default: `cp1251`) |
| `TEXT_UNDERLINE`| No      | Default underline mode (0/1) for printer text (default: `0`) |
| `TEXT_ALIGN`   | No       | Default alignment for printer text: `left`, `center`, or `right` (default: `left`) |
| `TEXT_WIDTH`   | No       | Default width multiplier for printer text (default: `2`) |
| `TEXT_HEIGHT`  | No       | Default height multiplier for printer text (default: `2`) |
| `TEXT_INVERT`  | No       | Default invert mode (0/1) for printer text (default: `0`) |
| `TEXT_SMOOTH`  | No       | Default smoothing for printer text (default: `false`) |
| `TEXT_FLIP`    | No       | Default flip mode for printer text (default: `false`) |
| `SERIAL_BYTESIZE` | No | Serial byte size (default: `8`) |
| `SERIAL_PARITY` | No | Serial parity (default: `N`) |
| `SERIAL_STOPBITS` | No | Serial stop bits (default: `1`) |
| `SERIAL_TIMEOUT` | No | Serial timeout in seconds (default: `1.0`) |
| `SERIAL_DSRDTR` | No | Enable DSR/DTR flow control (default: `true`) |

**Raspberry Pi / DietPi:** Enable serial in `raspi-config` → Interface Options → Serial Port.

The printer connection uses UART serial. Many ESC/POS printers work with 9600 baud, 8N1, and (depending on model) may require DSR/DTR flow control. This project defaults to those values (see the “Printing Text” example in the CircuitDigest guide) and you can override them via `.env` if needed. See: [Thermal Printer Interfacing with Raspberry Pi](https://circuitdigest.com/microcontroller-projects/thermal-printer-interfacing-with-raspberry-pi-zero-to-print-text-images-and-bar-codes).

---

## Usage

### Launch the application

```bash
python bot.py
```

The bot will start polling for updates. Send a message to your bot on Telegram to print it.

#### Run in background (screen)

```bash
screen -S bot python bot.py
```

Detach with `Ctrl+A`, then `D`. Reattach with `screen -r bot`.

#### Run as systemd service (Raspberry Pi)

Setup generates `bot.service` with the correct paths. Install for auto-start on boot:

```bash
python setup.py --install-service
sudo systemctl start bot
```

Or manually: copy `bot.service` to `/etc/systemd/system/`, edit paths if needed, then `sudo systemctl daemon-reload && sudo systemctl enable bot && sudo systemctl start bot`.

View status: `sudo systemctl status bot`. View logs: `journalctl -u bot -f`.

### Commands

| Command   | Description                           |
|-----------|---------------------------------------|
| `/start`  | Welcome message and basic instructions |
| `/status` | Check if the printer is online        |
| `/help`   | List all commands and limits          |

### Limits

- **Rate:** 1 print per 20 seconds per user (default, configurable via `PRINT_RATE_LIMIT_SECONDS`)
- **Text length:** Maximum 1000 characters per message

---

## Tests

The project uses [pytest](https://docs.pytest.org/) with [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) for async tests.

### Run all tests

```bash
pytest test/ -v
```

### Run specific test files

```bash
pytest test/test_bot.py -v    # Bot handlers, middleware, rate limiting
pytest test/test_printer.py -v # Printer module with mock
```

### Test coverage

Tests cover:
- **Bot:** Auth and throttling middleware, `/start`, `/status`, `/help`, print queue handler
- **Printer:** Initialization, `print_text`, `status` in mock mode

---

## Logging

Logging is configured with a **rotating file handler**:

- **File:** `logs/app.log`
- **Max size:** 10 MB per file
- **Backup count:** 5 (keeps up to 5 rotated files)
- **Level:** INFO

**Logged events include:**
- `Message received` — When text is queued for printing
- `Printed` / `Printed (mock)` — When a print job completes
- Errors with full tracebacks (print failures, handler exceptions, status check failures)

Logs are written to `logs/` (created automatically on startup). Ensure the application has write permissions to the project directory.
