"""Image tests: render the example layouts and compare them with saved reference images.

After an intended change in how things look, update the references and check them by eye:

    EPDLIB_UPDATE_IMAGES=1 uv run pytest tests/test_images.py
"""

import os
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from epdlib import Layout, ScreenMode

from .examples import EXAMPLES

REFERENCE = Path(__file__).parent / "images"
UPDATE = os.environ.get("EPDLIB_UPDATE_IMAGES") == "1"
MODES = {
    "bw": ScreenMode.bw(),
    "gray16": ScreenMode.gray(16),
    "7color": ScreenMode.palette(),
}
SCREENS = {"7in5": (800, 480), "2in7": (264, 176)}
# Share of pixels allowed to differ: font drawing can change slightly between Pillow builds.
TOLERANCE = 0.002


@pytest.mark.parametrize("screen", SCREENS)
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("example", EXAMPLES)
def test_example_matches_reference(example, mode, screen):
    data, values = EXAMPLES[example]
    width, height = SCREENS[screen]
    image = Layout(data).prepare(width, height, MODES[mode]).render(values)
    path = REFERENCE / f"{example}-{screen}-{mode}.png"
    if UPDATE or not path.exists():
        image.save(path)
        if not UPDATE:
            pytest.fail(f"no reference image yet; saved {path.name}, check it and run again")
        return
    expected = Image.open(path).convert(image.mode)
    assert expected.size == image.size
    diff = ImageChops.difference(image.convert("RGB"), expected.convert("RGB")).convert("L")
    changed = 1 - diff.histogram()[0] / (width * height)
    assert changed <= TOLERANCE, f"{changed:.2%} of pixels differ from {path.name}"
