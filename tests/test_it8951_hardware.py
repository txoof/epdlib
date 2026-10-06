"""Tests on a real IT8951 screen. Run on the Pi with the screen attached:

EPDLIB_IT8951_VCOM=-1.90 uv run pytest -m hardware tests/test_it8951_hardware.py
"""

import os
import time

import pytest
from PIL import Image, ImageDraw

pytestmark = pytest.mark.hardware


@pytest.fixture
def screen():
    from epdlib.drivers.it8951 import IT8951Driver

    vcom = os.environ.get("EPDLIB_IT8951_VCOM")
    if not vcom:
        pytest.skip("set EPDLIB_IT8951_VCOM to the value on the screen's ribbon cable")
    model = os.environ.get("EPDLIB_IT8951_MODEL", "9.7")
    with IT8951Driver(model, vcom=float(vcom)) as driver:
        yield driver
        driver.clear()
        driver.sleep()


def page_image(screen, n=0):
    """A test page: 16 gray bars and a numbered line of text."""
    w, h = screen.info.width, screen.info.height
    image = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(image)
    for i in range(16):  # 16 gray bars
        draw.rectangle((i * w // 16, 0, (i + 1) * w // 16, h // 4), fill=i * 17)
    draw.text((40, h // 2), f"epdlib IT8951 test {n}", fill=0, font_size=80)
    return image


def timed(call, *args, **kwargs) -> float:
    start = time.monotonic()
    call(*args, **kwargs)
    return time.monotonic() - start


def test_full_fast_and_clear(screen):
    assert timed(screen.clear) < 5
    assert timed(screen.write, page_image(screen)) < 3
    for n in range(1, 4):
        assert timed(screen.write, page_image(screen, n), fast=True) < 2
    assert timed(screen.write, page_image(screen, 3), fast=True) < 0.5  # nothing changed


def test_close_and_init_again(screen):
    screen.write(page_image(screen))
    screen.close()
    screen.init()
    screen.write(page_image(screen, 1), fast=True)
