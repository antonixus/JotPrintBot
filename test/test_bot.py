"""Comprehensive pytest suite for bot.py - handlers, middleware, rate limiting."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Patch config before importing bot (ensures whitelist, etc. are controllable)
@pytest.fixture(scope="module", autouse=True)
def patch_config():
    """Patch config for all bot tests."""
    with patch("config.WHITELIST", [111, 222]), patch(
        "config.ADMIN_ID", 999
    ), patch("printer.config") as pc:
        pc.MOCK_PRINTER = True
        pc.SERIAL_PORT = "/dev/serial0"
        pc.BAUDRATE = 9600
        pc.FONT = "12x24"
        pc.DENSITY_LEVEL = 4
        yield


@pytest.fixture
def mock_message():
    """Create a mock Message with from_user, text, reply, answer."""
    msg = MagicMock()
    msg.from_user = MagicMock()
    msg.from_user.id = 111
    msg.text = "Hello"
    msg.caption = None
    msg.reply = AsyncMock()
    msg.answer = AsyncMock()
    return msg


@pytest.fixture
def mock_event():
    """Create a mock event (Message-like) for middleware testing."""
    ev = MagicMock()
    ev.from_user = MagicMock()
    ev.from_user.id = 111
    ev.answer = AsyncMock()
    return ev


@pytest.fixture
def mock_handler():
    """Async handler that records calls."""
    async def handler(event, data):
        return "handled"

    return AsyncMock(side_effect=handler)


# --- Auth Middleware ---
class TestAuthMiddleware:
    """Tests for AuthMiddleware."""

    @pytest.mark.asyncio
    async def test_allows_whitelisted_user(self, mock_event, mock_handler):
        from bot import AuthMiddleware

        mw = AuthMiddleware()
        result = await mw(mock_handler, mock_event, {})
        assert result == "handled"
        mock_handler.assert_called_once()
        mock_event.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_denies_non_whitelisted_user(self, mock_event, mock_handler):
        from bot import AuthMiddleware

        mock_event.from_user.id = 99999  # not in WHITELIST [111, 222]
        mw = AuthMiddleware()
        result = await mw(mock_handler, mock_event, {})
        assert result is None
        mock_handler.assert_not_called()
        mock_event.answer.assert_called_once_with("Access denied")

    @pytest.mark.asyncio
    async def test_passes_through_when_from_user_is_none(self, mock_handler):
        from bot import AuthMiddleware

        ev = MagicMock()
        ev.from_user = None
        ev.answer = AsyncMock()
        mw = AuthMiddleware()
        result = await mw(mock_handler, ev, {})
        assert result == "handled"
        mock_handler.assert_called_once()


# --- Throttling Middleware ---
class TestThrottlingMiddleware:
    """Tests for ThrottlingMiddleware rate limiting."""

    @pytest.mark.asyncio
    async def test_allows_first_message(self, mock_event, mock_handler):
        from bot import ThrottlingMiddleware

        mw = ThrottlingMiddleware(key="test", rate_limit=1, period=60.0)
        result = await mw(mock_handler, mock_event, {})
        assert result == "handled"
        mock_handler.assert_called_once()
        mock_event.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_second_message_within_period(self, mock_event, mock_handler):
        from bot import ThrottlingMiddleware

        mw = ThrottlingMiddleware(key="test2", rate_limit=1, period=60.0)
        await mw(mock_handler, mock_event, {})
        mock_handler.reset_mock()
        result = await mw(mock_handler, mock_event, {})
        assert result is None
        mock_handler.assert_not_called()
        mock_event.answer.assert_called_once_with("Too many requests. Please wait.")

    @pytest.mark.asyncio
    async def test_allows_after_period_expires(self, mock_event, mock_handler):
        from bot import ThrottlingMiddleware
        from time import time as now

        mw = ThrottlingMiddleware(key="test3", rate_limit=1, period=0.1)
        await mw(mock_handler, mock_event, {})
        mock_handler.reset_mock()
        await asyncio.sleep(0.15)  # wait for period to expire
        result = await mw(mock_handler, mock_event, {})
        assert result == "handled"
        mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_through_when_from_user_is_none(self, mock_handler):
        from bot import ThrottlingMiddleware

        ev = MagicMock()
        ev.from_user = None
        ev.answer = AsyncMock()
        mw = ThrottlingMiddleware(key="test4", rate_limit=1, period=60.0)
        result = await mw(mock_handler, ev, {})
        assert result == "handled"
        mock_handler.assert_called_once()


# --- Handlers ---
class TestStartHandler:
    """Tests for /start handler."""

    @pytest.mark.asyncio
    async def test_start_replies_welcome(self, mock_message):
        from bot import start

        await start(mock_message)
        mock_message.reply.assert_called_once_with("Welcome! Send text to print.")


class TestStatusHandler:
    """Tests for /status handler."""

    @pytest.mark.asyncio
    async def test_status_replies_printer_online(self, mock_message):
        from bot import status_handler

        await status_handler(mock_message)
        mock_message.reply.assert_called_once()
        call_args = mock_message.reply.call_args[0][0]
        assert "Printer online:" in call_args


class TestHelpHandler:
    """Tests for /help handler."""

    @pytest.mark.asyncio
    async def test_help_lists_commands_and_limits(self, mock_message):
        from bot import help_handler

        await help_handler(mock_message)
        mock_message.reply.assert_called_once()
        text = mock_message.reply.call_args[0][0]
        assert "/start" in text
        assert "/status" in text
        assert "/help" in text
        assert "Rate:" in text
        assert "1000 characters" in text


class TestHandleMessage:
    """Tests for handle_message (print queue) handler."""

    @pytest.mark.asyncio
    async def test_empty_text_replies_send_text(self, mock_message):
        from bot import handle_message

        mock_message.text = ""
        mock_message.caption = None
        await handle_message(mock_message)
        mock_message.reply.assert_called_once_with("Send text to print.")

    @pytest.mark.asyncio
    async def test_too_long_replies_too_long(self, mock_message):
        from bot import handle_message

        mock_message.text = "x" * 1001
        await handle_message(mock_message)
        mock_message.reply.assert_called_once_with("Too long!")

    @pytest.mark.asyncio
    async def test_valid_text_queues_and_replies(self, mock_message):
        from bot import handle_message, printer

        # Drain queue from previous tests
        while not printer.queue.empty():
            printer.queue.get_nowait()
        mock_message.text = "Hello world"
        await handle_message(mock_message)
        mock_message.reply.assert_called_once_with("Queued for printing!")
        assert not printer.queue.empty()
        queued = await asyncio.wait_for(printer.queue.get(), timeout=0.5)
        assert "Hello" in queued

    @pytest.mark.asyncio
    async def test_uses_caption_when_text_empty(self, mock_message):
        from bot import handle_message, printer

        mock_message.text = None
        mock_message.caption = "Photo caption"
        await handle_message(mock_message)
        mock_message.reply.assert_called_once_with("Queued for printing!")
        queued = await asyncio.wait_for(printer.queue.get(), timeout=0.5)
        assert "Photo caption" in queued
