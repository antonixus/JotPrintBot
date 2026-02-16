"""Asynchronous Telegram bot for thermal printer."""

import asyncio
import logging
import tempfile
import uuid
from collections import defaultdict
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import time
from typing import Any, Awaitable, Callable

from aiogram import Bot, Dispatcher, BaseMiddleware, F
from aiogram.filters import Command
from aiogram.types import Message, TelegramObject
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.formatting import Text, Bold

import config
from printer import AsyncPrinter
from formatter import message_to_queue_item, QueueItem
from print_tasks import HeaderInfo, PrintTask, QrPayload, TextPayload, ImagePayload


def _build_header_info(message: Message) -> HeaderInfo:
    dt = message.date.astimezone()
    ts = dt.strftime("[%d.%m.%y %H:%M:%S]")
    username = getattr(message.from_user, "username", None)
    user = f"@{username}" if username else f"@id{message.from_user.id}"
    return HeaderInfo(timestamp=ts, user=user)

# Rotating file logging
Path("logs").mkdir(exist_ok=True)
_handler = RotatingFileHandler(
    "logs/app.log",
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
)
logging.basicConfig(handlers=[_handler], level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2),
)
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
    await message.reply(**Text("Welcome! Send text to print.").as_kwargs())


@dp.message(Command("status"))
async def status_handler(message: Message) -> None:
    """Handle /status command."""
    stat = await printer.status()
    online = bool(stat.get("online"))
    paper = stat.get("paper")
    if paper == 2:
        paper_text = "adequate"
    elif paper == 1:
        paper_text = "near-end"
    elif paper == 0:
        paper_text = "no paper"
    else:
        paper_text = "unknown"
    builder = Text(
        Bold("Printer online:"),
        f" {online}\n",
        Bold("Paper status:"),
        f" {paper_text}",
    )
    await message.reply(**builder.as_kwargs())


@dp.message(Command("help"))
async def help_handler(message: Message) -> None:
    """Handle /help command - list commands and limits."""
    seconds = config.PRINT_RATE_LIMIT_SECONDS
    builder = Text(
        Bold("Commands:"),
        "\n",
        "/start - Welcome and usage\n",
        "/status - Check printer online status\n",
        "/qr <text> - Print text as a QR code\n",
        "/help - List commands and limits\n\n",
        Bold("Telegram formatting → printer styles:"),
        "\n",
        "(when PRINT_TELEGRAM_FORMATTING=true)\n",
        "*bold* → bold / emphasized text\n",
        "__underline__ → underlined text\n",
        "~strikethrough~ → inverted text (white-on-black style via invert=True)\n",
        "`code` / triple-backtick blocks → printed with Font B (font='b', more compact/monospaced)\n",
        "> blockquote → double-size text (double_height=True, double_width=True)\n",
        "_italic_ entities are currently ignored\n\n",
        Bold("Limits:"),
        "\n",
        f"• Rate: 1 print per {seconds} seconds\n",
        "• Text length: max 1000 characters\n",
        "• QR text length: max 500 characters",
    )
    await message.reply(**builder.as_kwargs())


@dp.error()
async def error_handler(event: TelegramObject, exception: Exception) -> None:
    """Notify admin on handler exceptions."""
    logger.exception("Handler error: %s", exception)
    try:
        msg = Text("Error: ", str(exception))
        await bot.send_message(config.ADMIN_ID, **msg.as_kwargs())
    except Exception:
        pass


@dp.message(Command("qr"))
async def qr_handler(message: Message) -> None:
    """Handle /qr command - print a QR code with given text."""
    text = remove_command_from_message(message.text or "")
    if not text:
        await message.reply(**Text("Usage: /qr your text to encode").as_kwargs())
        return
    if len(text) > 500:
        await message.reply(**Text("QR content too long (max 500 characters).").as_kwargs())
        return
    logger.info("QR request from user %s: %s", message.from_user.id, text[:50])
    header = _build_header_info(message) if config.PRINT_HEADER_ENABLED else None
    task = PrintTask(header=header, payload=QrPayload(data=text))
    await printer.queue.put(task)
    await message.reply(**Text("QR code queued for printing!").as_kwargs())


@dp.message(F.photo)
async def photo_handler(message: Message) -> None:
    """Handle photo messages - download and queue for printing."""
    # Get largest photo size (F.photo filter ensures message.photo exists)
    photo = message.photo[-1]

    # Create temporary file path
    path = Path(tempfile.gettempdir()) / f"jotprint_{uuid.uuid4().hex}.jpg"

    try:
        # Download photo to temp file
        file = await bot.get_file(photo.file_id)
        await bot.download_file(file.file_path, path)
        logger.info("Photo downloaded from user %s: %s", message.from_user.id, path)
    except Exception as e:
        logger.exception("Photo download failed: %s", e)
        await message.reply(**Text("Failed to download image.").as_kwargs())
        return

    # Build header if enabled
    header = _build_header_info(message) if config.PRINT_HEADER_ENABLED else None

    # Enqueue print task
    task = PrintTask(header=header, payload=ImagePayload(image_path=str(path)))
    await printer.queue.put(task)
    await message.reply(**Text("Image queued for printing!").as_kwargs())


@dp.message()
async def handle_message(message: Message) -> None:
    """Handle arbitrary text to print."""
    text = message.text or message.caption or ""
    if not text.strip():
        await message.reply(**Text("Send text to print.").as_kwargs())
        return
    if len(text) > 1000:
        await message.reply(**Text("Too long!").as_kwargs())
        return
    logger.info("Message received from user %s: %s", message.from_user.id, text[:50])

    job: QueueItem
    if config.PRINT_TELEGRAM_FORMATTING:
        job = message_to_queue_item(message)
    else:
        job = (text or "").strip()

    header = _build_header_info(message) if config.PRINT_HEADER_ENABLED else None
    task = PrintTask(header=header, payload=TextPayload(content=job))
    await printer.queue.put(task)
    await message.reply(**Text("Queued for printing!").as_kwargs())

def remove_command_from_message(message_text: str) -> str:
    """Remove the leading /command (and its argument) from message.text."""
    if not message_text:
        return ""
    # Remove first token if it starts with "/"
    tokens = message_text.strip().split(maxsplit=1)
    if tokens and tokens[0].startswith("/"):
        return tokens[1] if len(tokens) > 1 else ""
    return message_text.strip()

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
            msg = Text("Error: ", str(e))
            await bot.send_message(config.ADMIN_ID, **msg.as_kwargs())
        except Exception:
            pass
        raise


if __name__ == "__main__":
    asyncio.run(main())
