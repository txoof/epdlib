"""Image tests: render the example layouts and compare them with saved reference images.

After an intended change in how things look (or a new Pillow version), update the
references on the Pi and check them by eye:

    EPDLIB_UPDATE_IMAGES=1 uv run pytest tests/test_images.py

The references are made on Linux with an ARM processor (the Raspberry Pi; CI uses ARM
machines too). Pillow's font drawing places letters a pixel apart on other processors,
so on other computers these tests are skipped.
"""

import base64
import io
import os
import platform
import sys
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


SAME_AS_PI = sys.platform == "linux" and platform.machine() in ("aarch64", "arm64")


@pytest.mark.skipif(
    not SAME_AS_PI,
    reason="reference images are made on Linux ARM (the Pi); font drawing differs elsewhere",
)
@pytest.mark.parametrize("screen", SCREENS)
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("example", EXAMPLES)
def test_example_matches_reference(example, mode, screen, extras):
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
    if changed > TOLERANCE:
        # Put the new image and the difference in the HTML test report, to look at.
        import pytest_html

        for title, picture in [("new image", image), ("difference", diff)]:
            buffer = io.BytesIO()
            picture.convert("RGB").save(buffer, "PNG")
            data = base64.b64encode(buffer.getvalue()).decode()
            extras.append(pytest_html.extras.png(data, name=title))
    assert changed <= TOLERANCE, f"{changed:.2%} of pixels differ from {path.name}"
