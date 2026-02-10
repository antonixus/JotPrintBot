## v0.1.0 – Printer configuration, Cyrillic support, and improved bot UX

### Printer configuration & encoding

- **New serial config options**: Added `.env` options for printer serial settings, including `SERIAL_BYTESIZE`, `SERIAL_PARITY`, `SERIAL_STOPBITS`, `SERIAL_TIMEOUT`, and `SERIAL_DSRDTR`.
- **Codepage and profile support**:
  - Introduced `CODEPAGE` (Python codec, default `cp1251`) to control how text is encoded before sending to the printer.
  - Added `CODEPAGE_ID` (ESC/POS code page ID, default `6` for cp1251) to select the correct hardware code page via `ESC t`.
  - Added `PRINTER_PROFILE` (default `RP326`) so `python-escpos` can use the correct printer capabilities.
- **`AsyncPrinter` updates**:
  - Initializes the printer and explicitly selects the configured ESC/POS code page using `ESC @` and `ESC t <CODEPAGE_ID>`.
  - Uses `python-escpos` `set()` for text style (font, density, width/height, underline, invert, smooth, flip) based on `.env` settings.
  - Encodes text using the configured `CODEPAGE` while preserving correct Cyrillic output on printers where code page 6 is `cp1251`.

### Status reporting

- **Enhanced `/status` command**:
  - Now shows **online status** using `escpos.is_online()`.
  - Also reports **paper status** using `escpos.paper_status()`:
    - `2` – paper adequate
    - `1` – paper near end
    - `0` – no paper
    - `unknown` – when the printer does not support status queries or an error occurs.
- **Mock support**:
  - Mock printer now implements `is_online()` and `paper_status()` so tests and mock mode are consistent with real hardware.

### Rate limiting improvements

- **Configurable print rate**:
  - Print rate limit is now controlled via `PRINT_RATE_LIMIT_SECONDS` (default **20 seconds** between prints per user).
- **Scoped rate limiting**:
  - `ThrottlingMiddleware` applies the limit **only to actual print messages**, not to commands.
  - Commands `/start`, `/help`, `/status`, and non-user events are no longer throttled.
- **Improved error message**:
  - When the rate limit is exceeded, users now see:
    - `Print rate limit exceeded. Limit 1 print per XX sec.`
    - `Please wait XX sec and try again.`

### Bot UX & commands

- `/help` output now shows the current print rate limit dynamically based on `PRINT_RATE_LIMIT_SECONDS`.
- `/start` and `/status` behaviors are preserved but are **never blocked** by the print rate limiter.

### Printer testing utilities

- `test/codepage_tables.py`:
  - Prints ESC/POS code page tables on the thermal printer.
  - Useful for verifying code page mappings and character sets for different printers.
- `test/test_encoding.py`:
  - Verifies Cyrillic output via `python-escpos.textln` using the configured printer profile and code page.
  - Confirms that text printed through the app matches raw cp1251 output behavior.

### Internal refactors & tests

- Centralized serial and text-style configuration in `config.py` and wired it through `AsyncPrinter`.
- Extended tests to cover:
  - Rate limiting behavior and error messages.
  - `/status` handler output including printer online and paper status.
- Ensured `MOCK_PRINTER=true` continues to work with the new APIs and configuration, so you can run and test the bot without a physical printer attached.

