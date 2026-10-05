import platform
from pathlib import Path

import pytest
from PIL import __version__ as pillow_version
from PIL import features

FONTS = Path(__file__).parent / "fonts"


def pytest_report_header(config):
    """Show what the image tests depend on at the top of the test output and report."""
    freetype = features.version("freetype2")
    raqm = features.version("raqm") or "not installed (epdlib does not use it)"
    return (
        f"Pillow {pillow_version}, FreeType {freetype}, raqm {raqm}, processor {platform.machine()}"
    )


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
