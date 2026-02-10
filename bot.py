"""Asynchronous Telegram bot for thermal printer."""

import asyncio
import logging
import textwrap
from collections import defaultdict
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import time
from typing import Any, Awaitable, Callable

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import Message, TelegramObject

import config
from printer import AsyncPrinter

# Rotating file logging
Path("logs").mkdir(exist_ok=True)
_handler = RotatingFileHandler(
    "logs/app.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
)
logging.basicConfig(handlers=[_handler], level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()
printer = AsyncPrinter()


# --- Auth middleware ---
class AuthMiddleware(BaseMiddleware):
    """Allow only whitelisted users."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if event.from_user is None:
            return await handler(event, data)
        if event.from_user.id not in config.WHITELIST:
            await event.answer("Access denied")
            return
        return await handler(event, data)


# --- Throttling middleware (1 msg / N sec per user, scoped by key) ---
class ThrottlingMiddleware(BaseMiddleware):
    """Rate limit: rate_limit msgs per period seconds per user, scoped by key."""

    def __init__(
        self, key: str = "default", rate_limit: int = 1, period: float = 60.0
    ) -> None:
        self.key = key
        self.rate_limit = rate_limit
        self.period = period
        self.user_timestamps: dict[tuple[str, int], list[float]] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Pass through if there is no user (e.g. service updates)
        if event.from_user is None:
            return await handler(event, data)

        # Do not apply rate limiting to command messages like /start, /help, /status.
        # The limit should only apply to actual text that is sent to the printer.
        if isinstance(event, Message) and event.text and event.text.startswith("/"):
            return await handler(event, data)

        uid = event.from_user.id
        bucket = (self.key, uid)
        now = time()
        timestamps = self.user_timestamps[bucket]
        timestamps[:] = [t for t in timestamps if now - t < self.period]
        if len(timestamps) >= self.rate_limit:
            seconds = int(self.period)
            await event.answer(
                f"Print rate limit exceeded. Limit 1 print per {seconds} sec.\n"
                f"Please wait {seconds} sec and try again."
            )
            return
        timestamps.append(now)
        return await handler(event, data)


# --- Handlers ---
@dp.message(Command("start"))
async def start(message: Message) -> None:
    """Handle /start command."""
    await message.reply("Welcome! Send text to print.")


@dp.message(Command("status"))
async def status_handler(message: Message) -> None:
    """Handle /status command."""
    stat = await printer.status()
    online = bool(stat.get("online"))
    paper = stat.get("paper")
    paper_text = "unknown"
    if paper in (0, 1, 2):
        paper_text = f"{paper} (2=adequate, 1=near-end, 0=no paper)"
    await message.reply(
        f"Printer online: {online}\n"
        f"Paper status: {paper_text}"
    )


@dp.message(Command("help"))
async def help_handler(message: Message) -> None:
    """Handle /help command - list commands and limits."""
    seconds = config.PRINT_RATE_LIMIT_SECONDS
    help_text = (
        "Commands:\n"
        "/start - Welcome and usage\n"
        "/status - Check printer online status\n"
        "/qr <text> - Print text as a QR code\n"
        "/help - List commands and limits\n\n"
        "Limits:\n"
        f"• Rate: 1 print per {seconds} seconds\n"
        "• Text length: max 1000 characters\n"
        "• QR text length: max 500 characters"
    )
    await message.reply(help_text)


@dp.error()
async def error_handler(event: TelegramObject, exception: Exception) -> None:
    """Notify admin on handler exceptions."""
    logger.exception("Handler error: %s", exception)
    try:
        await bot.send_message(config.ADMIN_ID, f"Error: {exception}")
    except Exception:
        pass


@dp.message(Command("qr"))
async def qr_handler(message: Message) -> None:
    """Handle /qr command - print a QR code with given text."""
    text = (message.text or "").partition(" ")[2].strip()
    if not text:
        await message.reply("Usage: /qr your text to encode")
        return
    if len(text) > 500:
        await message.reply("QR content too long (max 500 characters).")
        return
    logger.info("QR request from user %s: %s", message.from_user.id, text[:50])
    try:
        await printer.print_qr(text)
    except Exception as e:
        logger.error("QR print failed: %s", e, exc_info=True)
        await message.reply("Failed to print QR code.")
        return
    await message.reply("QR code sent to printer!")


@dp.message()
async def handle_message(message: Message) -> None:
    """Handle arbitrary text to print."""
    text = message.text or message.caption or ""
    if not text.strip():
        await message.reply("Send text to print.")
        return
    if len(text) > 1000:
        await message.reply("Too long!")
        return
    logger.info("Message received from user %s: %s", message.from_user.id, text[:50])
    # Set text wrapping width based on font: Font A = 42 columns, Font B = 56 columns
    wrap_width = 42 if config.FONT.lower() == "a" else 56
    wrapped = textwrap.fill(text, width=wrap_width)
    await printer.queue.put(wrapped)
    await message.reply("Queued for printing!")


# --- Setup ---
def setup() -> None:
    """Register middleware and router."""
    dp.message.middleware(AuthMiddleware())
    dp.message.middleware(
        ThrottlingMiddleware(
            key="print", rate_limit=1, period=float(config.PRINT_RATE_LIMIT_SECONDS)
        )
    )


async def main() -> None:
    """Run bot with polling."""
    setup()
    asyncio.create_task(printer._process_queue())
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception("Bot error: %s", e)
        try:
            await bot.send_message(config.ADMIN_ID, f"Error: {e}")
        except Exception:
            pass
        raise


if __name__ == "__main__":
    asyncio.run(main())
