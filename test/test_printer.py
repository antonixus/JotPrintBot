"""Pytest tests for printer module with MOCK_PRINTER=True."""

import pytest
from unittest.mock import patch

from printer import AsyncPrinter, MockPrinter


@pytest.fixture(autouse=True)
def mock_config():
    """Force MOCK_PRINTER=True for all tests."""
    with patch("printer.config") as mock_cfg:
        mock_cfg.MOCK_PRINTER = True
        mock_cfg.SERIAL_PORT = "/dev/serial0"
        mock_cfg.BAUDRATE = 9600
        mock_cfg.FONT = "12x24"
        mock_cfg.DENSITY_LEVEL = 4
        yield mock_cfg


class TestAsyncPrinterInit:
    """Tests for AsyncPrinter.__init__."""

    def test_init_uses_mock_printer_when_mock_true(self, mock_config):
        """Printer should be MockPrinter instance when MOCK_PRINTER=True."""
        mock_config.MOCK_PRINTER = True
        p = AsyncPrinter()
        assert isinstance(p.printer, MockPrinter)

    def test_init_creates_queue(self, mock_config):
        """Should create an empty asyncio.Queue."""
        p = AsyncPrinter()
        assert p.queue.empty()
        assert p.queue.qsize() == 0

    def test_init_sets_mock_flag(self, mock_config):
        """_mock should be True when MOCK_PRINTER=True."""
        p = AsyncPrinter()
        assert p._mock is True


@pytest.mark.asyncio
class TestAsyncPrinterPrintText:
    """Tests for AsyncPrinter.print_text."""

    async def test_print_text_logs_when_mock(self, mock_config, caplog):
        """Should log 'Mock print:' when printing in mock mode."""
        import logging

        caplog.set_level(logging.INFO)
        p = AsyncPrinter()
        await p.print_text("Hello, world!")
        assert "Printed (mock): Hello, world!" in caplog.text

    async def test_print_text_completes_without_error(self, mock_config):
        """print_text should not raise in mock mode."""
        p = AsyncPrinter()
        await p.print_text("Test message")

    async def test_print_text_handles_empty_string(self, mock_config, caplog):
        """Should handle empty string."""
        import logging

        caplog.set_level(logging.INFO)
        p = AsyncPrinter()
        await p.print_text("")
        assert "Printed (mock):" in caplog.text


@pytest.mark.asyncio
class TestAsyncPrinterStatus:
    """Tests for AsyncPrinter.status."""

    async def test_status_returns_online_true_when_mock(self, mock_config):
        """Status should return online=True and paper=2 in mock mode."""
        p = AsyncPrinter()
        result = await p.status()
        assert result == {"online": True, "paper": 2}

    async def test_status_is_async(self, mock_config):
        """status() should be awaitable and return dict."""
        p = AsyncPrinter()
        result = await p.status()
        assert isinstance(result, dict)
        assert "online" in result
        assert "paper" in result


@pytest.mark.asyncio
class TestAsyncPrinterPrintQR:
    """Tests for AsyncPrinter.print_qr."""

    async def test_print_qr_logs_when_mock(self, mock_config, caplog):
        """Should log 'QR printed (mock)' when printing QR in mock mode."""
        import logging

        caplog.set_level(logging.INFO)
        p = AsyncPrinter()
        await p.print_qr("Привет")
        assert "QR printed (mock): Привет" in caplog.text

    async def test_print_qr_completes_without_error(self, mock_config):
        """print_qr should not raise in mock mode."""
        p = AsyncPrinter()
        await p.print_qr("Test QR")
