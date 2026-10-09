"""Tests on a real Waveshare screen. Run on the Pi with the screen attached:

uv run pytest -m hardware tests/test_waveshare_hardware.py

For another screen than the 7.5" V2, set EPDLIB_WAVESHARE_MODEL to its name in
docs/waveshare.md. Set EPDLIB_WAVESHARE_NO_POWER_PIN=1 to leave GPIO 18 alone.
"""

import os
import time

import pytest
from PIL import Image, ImageDraw

pytestmark = pytest.mark.hardware


@pytest.fixture
def screen():
    from epdlib.drivers.waveshare import WaveshareDriver

    model = os.environ.get("EPDLIB_WAVESHARE_MODEL", "epd7in5_V2")
    options = {"power_pin": None} if os.environ.get("EPDLIB_WAVESHARE_NO_POWER_PIN") else {}
    with WaveshareDriver(model, **options) as driver:
        yield driver
        driver.clear()
        driver.sleep()


def page_image(screen, n=0):
    """A test page: a frame, a black bar, a dithered gray bar and a numbered line of text."""
    w, h = screen.info.width, screen.info.height
    image = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, w - 1, h - 1), outline=0, width=4)
    draw.rectangle((w // 10, h // 10, w // 2, h // 5), fill=0)
    draw.rectangle((w // 2, h // 10, w * 9 // 10, h // 5), fill=128)
    draw.text((w // 10, h // 2), f"epdlib Waveshare test {n}", fill=0, font_size=h // 10)
    return image


def timed(call, *args, **kwargs) -> float:
    start = time.monotonic()
    call(*args, **kwargs)
    return time.monotonic() - start


def test_clear_write_and_sleep(screen):
    assert timed(screen.clear) < 10
    assert timed(screen.write, page_image(screen)) < 10
    assert timed(screen.sleep) < 5


def test_write_wakes_a_sleeping_screen(screen):
    screen.write(page_image(screen))
    screen.sleep()
    assert timed(screen.write, page_image(screen, 1)) < 10


def test_close_and_init_again(screen):
    screen.write(page_image(screen))
    screen.close()
    screen.init()
    screen.write(page_image(screen, 1))
