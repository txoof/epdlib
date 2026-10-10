"""All Waveshare models in the table, run against the fake HAT (tests/fake_waveshare.py).

Only the 7.5" V2 is tested in detail (tests/test_waveshare.py); here every model must at
least load, start, write, clear, sleep and wake with Waveshare's own file.
"""

import importlib
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from epdlib.drivers.waveshare import _TABLE, MODELS, NOT_WORKING, WaveshareDriver, _name
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
        assert colour == screen._epd.getbuffer(Image.new("1", image.size, 1))
        assert black != colour


def test_2in7b_uses_the_black_and_white_2in7_file():
    with WaveshareDriver("epd2in7b", board=FakeBoard(idle=None)) as screen:
        assert type(screen._epd).__module__ == f"{PACKAGE}.epd2in7"
    assert MODELS["epd2in7b"].model == 'Waveshare 2.7" B (black and white only)'


def test_unused_imports_get_stand_ins_that_do_not_stay(monkeypatch):
    for name in ("RPi", "RPi.GPIO", f"{PACKAGE}.epd2in9d"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    with WaveshareDriver("epd2in9d", board=FakeBoard(idle=None)) as screen:
        screen.write(page(MODELS["epd2in9d"]))
    try:
        importlib.import_module("RPi.GPIO")
    except ImportError:
        assert "RPi.GPIO" not in sys.modules  # the stand-in was removed again


@pytest.mark.parametrize(
    ("model", "colours"), [("epd5in65f", 7), ("epd4in01f", 7), ("epd7in3f", 7), ("epd2in13g", 4)]
)
def test_palette_colours_match_waveshare_values(model, colours):
    """Waveshare's files turn each palette colour into its own number: a colour that is a
    little off would become another one (or black, in epd4in01f)."""
    info = MODELS[model]
    image = Image.new("RGB", (info.width, info.height), "white")
    draw = ImageDraw.Draw(image)
    for i, colour in enumerate(info.mode.colors):
        draw.rectangle((i * 16, 0, i * 16 + 15, info.height - 1), fill=colour)
    with WaveshareDriver(model, board=FakeBoard(idle=None)) as screen:
        buffer = bytes(screen._epd.getbuffer(screen.check_image(image)))
    bits = 4 if colours == 7 else 2
    codes = {(byte >> shift) & (2**bits - 1) for byte in buffer for shift in range(0, 8, bits)}
    assert len(codes) == len(info.mode.colors) == colours


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
