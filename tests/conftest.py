import platform
from pathlib import Path

import pytest
from PIL import __version__ as pillow_version
from PIL import features

FONTS = Path(__file__).parent / "fonts"


def pytest_report_header(config):
    """Show what the image tests depend on at the top of the test output and report."""
    freetype = features.version("freetype2")
    return f"Pillow {pillow_version}, FreeType {freetype}, processor {platform.machine()}"


@pytest.fixture
def italic_font() -> str:
    """DejaVu Serif Italic: letters such as f and j reach left of where the text starts."""
    return str(FONTS / "DejaVuSerif-Italic.ttf")


def text_block(name="t", **options):
    return {"name": name, "type": "text", **options}


def column(*items, **options):
    return {"column": list(items), **options}


def row(*items, **options):
    return {"row": list(items), **options}


def pytest_report_header(config):  # TEMPORARY: debug measurements
    from PIL import Image, ImageChops, ImageDraw

    from epdlib.text import load_font

    f = load_font(None, 200)
    out = [f"freetype {features.version('freetype2')}"]
    for t in ["12:47", "12:", ":4", "47"]:
        out.append(f"{t} len={f.getlength(t)} bbox={f.getbbox(t, anchor='ls')}")
    im = Image.new("L", (900, 300), 255)
    ImageDraw.Draw(im).text((10, 250), "12:47", font=f, anchor="ls")
    out.append(f"ink={ImageChops.invert(im).getbbox()} sum={sum(im.histogram()[:128])}")
    return out
