"""Tests for image enhancement functionality."""

import pytest
from PIL import Image
import config
from printer import AsyncPrinter


class TestImageEnhancement:
    """Test image enhancement in _enhance_image method."""

    def test_enhance_contrast(self):
        """Test contrast enhancement."""
        printer = AsyncPrinter()
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))  # Gray image
        enhanced = printer._enhance_image(img)

        assert enhanced is not None
        assert enhanced.mode in ("L", "1")  # Grayscale or binary

    def test_enhance_sharpness(self):
        """Test sharpness enhancement."""
        printer = AsyncPrinter()
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        enhanced = printer._enhance_image(img)

        assert enhanced is not None

    def test_enhance_brightness(self):
        """Test brightness enhancement."""
        printer = AsyncPrinter()
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        enhanced = printer._enhance_image(img)

        assert enhanced is not None

    def test_enhance_grayscale(self):
        """Test grayscale conversion."""
        printer = AsyncPrinter()
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))  # Red
        enhanced = printer._enhance_image(img)

        assert enhanced is not None
        assert enhanced.mode in ("L", "1")  # Should be grayscale or binary

    def test_enhance_dithering(self):
        """Test dithering for smooth gradients."""
        printer = AsyncPrinter()
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        enhanced = printer._enhance_image(img)

        assert enhanced is not None
        assert enhanced.mode in ("L", "1")  # Binary after dithering

    def test_enhance_disabled(self):
        """Test enhancement when disabled."""
        # Temporarily disable enhancements
        original_contrast = config.IMAGE_CONTRAST
        original_sharpness = config.IMAGE_SHARPNESS
        original_brightness = config.IMAGE_BRIGHTNESS
        original_grayscale = config.IMAGE_GRAYSCALE
        original_dithering = config.IMAGE_DITHERING

        try:
            config.IMAGE_CONTRAST = 1.0
            config.IMAGE_SHARPNESS = 1.0
            config.IMAGE_BRIGHTNESS = 1.0
            config.IMAGE_GRAYSCALE = False
            config.IMAGE_DITHERING = False

            printer = AsyncPrinter()
            img = Image.new("RGB", (100, 100), color=(128, 128, 128))
            enhanced = printer._enhance_image(img)

            assert enhanced is not None
            assert enhanced.mode == "RGB"  # Should remain RGB

        finally:
            # Restore original values
            config.IMAGE_CONTRAST = original_contrast
            config.IMAGE_SHARPNESS = original_sharpness
            config.IMAGE_BRIGHTNESS = original_brightness
            config.IMAGE_GRAYSCALE = original_grayscale
            config.IMAGE_DITHERING = original_dithering