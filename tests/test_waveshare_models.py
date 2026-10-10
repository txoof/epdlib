"""All Waveshare models in the table, run against the fake HAT (tests/fake_waveshare.py).

Only the 7.5" V2 is tested in detail (tests/test_waveshare.py); here every model must at
least load, start, write, clear, sleep and wake with Waveshare's own file.
"""

import importlib
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from epdlib.drivers.waveshare import (
    _TABLE,
    MODELS,
    NOT_WORKING,
    WaveshareDriver,
    _name,
    _stand_ins,
)
from epdlib.drivers.waveshare.vendor import epdconfig
from tests.fake_waveshare import FakeBoard

VENDOR = Path(epdconfig.__file__).parent
PACKAGE = "epdlib.drivers.waveshare.vendor"


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    monkeypatch.setattr(epdconfig, "delay_ms", lambda ms: None)


def page(info):
    image = Image.new("RGB", (info.width, info.height), "white")
    ImageDraw.Draw(image).rectangle((5, 5, 40, 30), fill="black")
    return image


@pytest.mark.parametrize("model", MODELS)
def test_every_model_runs(model):
    info = MODELS[model]
    fake = FakeBoard(idle=None)
    with WaveshareDriver(model, board=fake, timeout=60) as screen:
        screen.write(page(info))
        screen.clear()
        screen.sleep()
        assert fake.pins[18] is False  # sleep switched the power off
        sent = len(fake.sent)
        screen.write(page(info))  # wakes the screen
        assert fake.pins[18] is True and len(fake.sent) > sent
    assert fake.closed == 1


def test_every_copied_file_is_a_model_or_listed_as_not_working():
    files = {p.stem for p in VENDOR.glob("epd*.py")} - {"epdconfig"}
    used = set(MODELS) | {row[3].file for row in _TABLE.values() if row[3].file}
    assert files == used | set(NOT_WORKING)
    assert not set(MODELS) & set(NOT_WORKING)


@pytest.mark.parametrize("model", MODELS)
def test_sizes_match_waveshare_files_wide_side_first(model):
    info = MODELS[model]
    file = _TABLE[model][3].file or model
    with WaveshareDriver(model, board=FakeBoard(idle=None)) as screen:
        module = screen._module()
    size = (module.EPD_WIDTH, module.EPD_HEIGHT)
    assert (info.width, info.height) == (max(size), min(size)), file


@pytest.mark.parametrize("model", NOT_WORKING)
def test_not_working_models_are_refused(model):
    with pytest.raises(ValueError, match="does not work"):
        WaveshareDriver(model)


def test_three_colour_screens_get_an_empty_colour_layer():
    info = MODELS["epd2in13b_V3"]
    assert info.model == 'Waveshare 2.13" B V3 (black and white only)'
    with WaveshareDriver("epd2in13b_V3", board=FakeBoard(idle=None)) as screen:
        calls = []
        screen._epd.display = lambda black, colour: calls.append((black, colour))
        image = page(info)
        screen.write(image)
        black, colour = calls[0]
        assert black == screen._epd.getbuffer(screen.check_image(image))
        assert colour == screen._epd.getbuffer(Image.new("1", image.size, 255))
        assert black != colour


def test_2in7b_uses_the_black_and_white_2in7_file():
    with WaveshareDriver("epd2in7b", board=FakeBoard(idle=None)) as screen:
        assert type(screen._epd).__module__ == f"{PACKAGE}.epd2in7"
    assert MODELS["epd2in7b"].model == 'Waveshare 2.7" B (black and white only)'


def test_stand_ins_are_added_only_for_missing_modules_and_removed_again():
    with _stand_ins({"nosuchpkg.sub": {"x": 1}, "json": {"x": 1}}):
        assert sys.modules["nosuchpkg.sub"].x == 1
        assert "x" not in vars(sys.modules["json"])  # a real module is left alone
    assert "nosuchpkg" not in sys.modules and "nosuchpkg.sub" not in sys.modules
    assert "json" in sys.modules


def test_files_with_unused_imports_load(monkeypatch):
    for name in (
        "RPi",
        "RPi.GPIO",
        "distutils",
        "distutils.command",
        "distutils.command.build_scripts",
        f"{PACKAGE}.epd2in9d",
    ):
        monkeypatch.delitem(sys.modules, name, raising=False)
    # Pretend the libraries are missing, whatever is installed here.
    monkeypatch.setitem(sys.modules, "RPi", None)
    monkeypatch.setitem(sys.modules, "distutils", None)
    with WaveshareDriver("epd2in9d", board=FakeBoard(idle=None)) as screen:
        screen.write(page(MODELS["epd2in9d"]))
    assert sys.modules["RPi"] is None and sys.modules["distutils"] is None


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("epd2in13_V2", ["FULL_UPDATE"]),
        ("epd1in54_V2", [False]),
        ("epd3in7", [1]),
        ("epd1in54", ["lut_full_update"]),
    ],
)
def test_init_gets_the_full_refresh_arguments(model, expected, monkeypatch):
    module = importlib.import_module(f"{PACKAGE}.{model}")
    seen = []
    monkeypatch.setattr(module.EPD, "init", lambda epd, *args: seen.append(list(args)) or 0)
    with WaveshareDriver(model, board=FakeBoard(idle=None)) as screen:
        values = [getattr(screen._epd, v) if isinstance(v, str) else v for v in expected]
    assert seen == [values]


def test_3in52_write_refreshes_the_screen():
    """Waveshare's epd3in52 display() only sends the image; the refresh is a separate step."""
    fake = FakeBoard(idle=None)
    with WaveshareDriver("epd3in52", board=fake) as screen:
        screen.write(page(MODELS["epd3in52"]))
        commands = fake.commands
    assert commands[-1] == 0x17 and 0x13 in commands  # image, then refresh


def test_clear_on_a_colour_screen_records_white():
    with WaveshareDriver("epd5in65f", board=FakeBoard(idle=None)) as screen:
        screen.clear()
        assert screen._shown.getcolors() == [(600 * 448, (255, 255, 255))]


# Waveshare's number for each of our palette colours, in the order of the palette
# (epd7in3e skips 4, which Waveshare's palette fills with a second black).
CODES = {
    "epd5in65f": range(7),
    "epd4in01f": range(7),
    "epd7in3f": range(7),
    "epd4in37g": range(4),
    "epd7in3g": range(4),
    "epd7in3e": [0, 1, 2, 3, 5, 6],
}


@pytest.mark.parametrize("model", CODES)
def test_palette_colours_match_waveshare_values(model):
    """Waveshare's files turn each palette colour into its own number: a colour that is a
    little off would become another one (or black, in epd4in01f)."""
    info = MODELS[model]
    bits = 4 if len(info.mode.colors) > 4 else 2
    with WaveshareDriver(model, board=FakeBoard(idle=None)) as screen:
        for colour, code in zip(info.mode.colors, CODES[model], strict=True):
            image = Image.new("RGB", (info.width, info.height), colour)
            buffer = bytes(screen._epd.getbuffer(screen.check_image(image)))
            codes = {(b >> shift) & (2**bits - 1) for b in buffer for shift in range(0, 8, bits)}
            assert codes == {code}, colour


@pytest.mark.parametrize(
    ("file", "name"),
    [
        ("epd7in5_V2", '7.5" V2'),
        ("epd2in13bc", '2.13" B/C'),
        ("epd7in5b_V2_old", '7.5" B V2 (old)'),
        ("epd13in3k", '13.3" K'),
        ("epd1in02", '1.02"'),
        ("epd7in5_HD", '7.5" HD'),
    ],
)
def test_names(file, name):
    assert _name(file) == name


def test_white_stored_as_1_in_a_1_bit_image_stays_white():
    """Pillow keeps 1 (not 255) for a white pixel set to 1; epd5in83's file takes values
    below 64 as black, which once turned a whole test page black on the screen."""
    info = MODELS["epd5in83"]
    image = Image.new("1", (info.width, info.height), 1)
    image.putpixel((0, 0), 0)
    with WaveshareDriver("epd5in83", board=FakeBoard(idle=None)) as screen:
        calls = []
        screen._epd.display = calls.append
        screen.write(image)
    buffer = calls[0]  # 2 bits per pixel: 0b00 black, 0b11 white
    assert buffer[0] == 0b00111111 and set(buffer[1:]) == {0xFF}
