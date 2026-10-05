from pathlib import Path

import pytest

FONTS = Path(__file__).parent / "fonts"


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
