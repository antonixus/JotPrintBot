# JotPrintBot

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://github.com/antonixus/JotPrintBot/blob/main/LICENSE)

## Introduction

**JotPrintBot** is an asynchronous Python application that allows you to print text from Telegram messages to a thermal receipt printer. Send a message to the bot, and it will be printed on paper via a connected ESC/POS thermal printer.

**Supported hardware:**
- **CSN-A2 TTL** thermal printer (and other ESC/POS compatible models)
- **Raspberry Pi** / **DietPi** (serial connection via `/dev/serial0` or similar)
- Any Linux system with a serial or USB-Serial thermal printer

The bot uses [aiogram](https://docs.aiogram.dev/) for Telegram integration and [python-escpos](https://python-escpos.readthedocs.io/) for printer control.

---

## Functionality

- **Print text** — Send any text message (up to 1000 characters); it will be wrapped to the printer’s font width and queued for printing:
  - `FONT=a` (Font A): 42 characters per line
  - `FONT=b` (Font B): 56 characters per line
- **Whitelist access** — Only users in the whitelist can use the bot; others receive "Access denied"
- **Rate limiting** — 1 print per 10 seconds per user by default (configurable via `PRINT_RATE_LIMIT_SECONDS`)
- **Telegram formatting → printer styles** (when `PRINT_TELEGRAM_FORMATTING=true`):
  - `*bold*` → bold / emphasized text
  - `__underline__` → underlined text
  - `~strikethrough~` → double‑strike mode (same visual weight as emphasized on CSN‑A2)
  - `` `code` `` / triple‑backtick blocks → printed with Font **B** (`font='b'`, more compact/monospaced)
  - `> blockquote` → emphasized text (no extra frame)
  - `_italic_` entities are currently **ignored** (no rotation/italic on printer)
- **Commands:**
  - `/start` — Welcome message and usage instructions
  - `/status` — Check if the printer is online and paper status (adequate / near-end / no paper)
  - `/help` — List commands and limits
  - `/qr <text>` — Print the given text as a QR code (UTF-8 safe, supports Cyrillic)
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
git clone https://github.com/antonixus/JotPrintBot.git
cd JotPrintBot
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
| `PRINT_RATE_LIMIT_SECONDS` | No | Seconds between prints per user (default: `10`) |
| `CODEPAGE`     | No       | Python codec name for text encoding before sending to printer (default: `cp1251`) |
| `CODEPAGE_ID`  | No       | ESC/POS code page ID used with `ESC t` (on many printers `6` is cp1251; default: `6`) |
| `PRINTER_PROFILE` | No    | python-escpos printer profile name (default: `RP326`) |
| `MEDIA_WIDTH_PIXELS` | No    | Printer media width in pixels |
| `MEDIA_WIDTH_MM` | No    | Printer media width in mm |
| `TEXT_UNDERLINE`| No      | Default underline mode (0/1) for printer text (default: `0`) |
| `TEXT_ALIGN`   | No       | Default alignment for printer text: `left`, `center`, or `right` (default: `left`) |
| `TEXT_WIDTH`   | No       | Default width multiplier for printer text (default: `1`) |
| `TEXT_HEIGHT`  | No       | Default height multiplier for printer text (default: `1`) |
| `TEXT_INVERT`  | No       | Default invert mode (0/1) for printer text (default: `0`) |
| `TEXT_SMOOTH`  | No       | Default smoothing for printer text (default: `false`) |
| `TEXT_FLIP`    | No       | Default flip mode for printer text (default: `false`) |
| `SERIAL_BYTESIZE` | No | Serial byte size (default: `8`) |
| `SERIAL_PARITY` | No | Serial parity (default: `N`) |
| `SERIAL_STOPBITS` | No | Serial stop bits (default: `1`) |
| `SERIAL_TIMEOUT` | No | Serial timeout in seconds (default: `1.0`) |
| `SERIAL_DSRDTR` | No | Enable DSR/DTR flow control (default: `true`) |
| `QR_SIZE`      | No       | Default QR code pixel size 1–16 (default: `3`) |
| `QR_ALIGN`     | No       | Base alignment before printing QR codes: `left`, `center`, or `right` (default: `center`) |
| `QR_DENSITY`   | No       | Print density used for QR codes (default: `3`) |
| `QR_CENTER`    | No       | Center QR image when using software-rendered QR (default: `false`, example: `true`) |
| `QR_IMG_IMPL`  | No       | Image implementation for QR rendering: `bitImageRaster`, `graphics`, or `bitImageColumn` (default: `bitImageRaster`, example: `bitImageColumn`) |

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

| Command   | Description                                    |
|-----------|------------------------------------------------|
| `/start`  | Welcome message and basic instructions         |
| `/status` | Check if the printer is online and paper status |
| `/help`   | List all commands and limits                  |
| `/qr`     | Print a QR code with the given text           |

### Limits

- **Rate:** 1 print per 10 seconds per user (default, configurable via `PRINT_RATE_LIMIT_SECONDS`)
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
pytest test/test_printer.py -v   # Printer module with mock (text & QR)
pytest test/test_wrapping.py -v  # Font-based wrapping expectations
pytest test/test_encoding.py -v  # Cyrillic encoding on real printer (requires hardware)
```

### Test coverage

Tests cover:
- **Printer (mock):** Initialization, `print_text`, `print_qr`, `status` in mock mode
- **Wrapping helper scripts:** How many characters fit per line for different fonts
- **Encoding helper script:** Cyrillic output validation using the configured printer profile and code page

For QR-specific manual testing, you can also use:

```bash
python -m test.qr_print_test "Hello" --impl bitImageColumn --center
```

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
