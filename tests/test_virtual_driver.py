import pytest
from PIL import Image

from epdlib import ScreenMode
from epdlib.drivers import DisplayError
from epdlib.drivers.virtual import VirtualDriver


def test_write_saves_png(tmp_path):
    with VirtualDriver(100, 50, ScreenMode.bw(), tmp_path) as display:
        display.write(Image.new("L", (100, 50), 0))
    saved = Image.open(tmp_path / "latest.png")
    assert saved.size == (100, 50)
    assert saved.mode == "1"
    assert (tmp_path / "0001.png").exists()


def test_close_runs_after_error(tmp_path):
    display = VirtualDriver(10, 10, ScreenMode.bw(), tmp_path)
    with pytest.raises(RuntimeError), display:
        raise RuntimeError("boom")
    assert display.log[-1] == ("close",)


def test_wrong_size_is_an_error(tmp_path):
    with VirtualDriver(100, 50, ScreenMode.bw(), tmp_path) as display:
        with pytest.raises(DisplayError, match="screen is 100x50"):
            display.write(Image.new("L", (50, 50)))


def test_write_and_clear_after_sleep_wake_the_screen(tmp_path):
    with VirtualDriver(10, 10, ScreenMode.bw(), tmp_path) as display:
        display.write(Image.new("1", (10, 10)))
        display.sleep()
        display.write(Image.new("1", (10, 10)), fast=True)
        display.sleep()
        display.sleep()  # sleeping again changes nothing
        display.clear()
    assert display.log == [
        ("init",),
        ("write", "full"),
        ("sleep",),
        ("wake",),
        ("write", "fast"),
        ("sleep",),
        ("sleep",),
        ("wake",),
        ("clear",),
        ("close",),
    ]


@pytest.mark.parametrize(
    "before",
    [[], ["sleep"], ["init", "close"], ["init", "close", "sleep"], ["init", "sleep", "close"]],
)
def test_write_before_init_or_after_close_needs_init(tmp_path, before):
    display = VirtualDriver(10, 10, ScreenMode.bw(), tmp_path)
    for name in before:
        getattr(display, name)()
    with pytest.raises(DisplayError, match="closed: call init"):
        display.write(Image.new("1", (10, 10)))
    with pytest.raises(DisplayError, match="closed: call init"):
        display.clear()


def test_fast_refresh_when_supported(tmp_path):
    with VirtualDriver(10, 10, ScreenMode.bw(), tmp_path, fast_refresh=True) as display:
        display.write(Image.new("1", (10, 10)), fast=True)
    assert ("write", "fast") in display.log


@pytest.mark.parametrize("options", [{"timeout": 0}, {"timeout": -1}, {"keep": 0}])
def test_bad_settings(tmp_path, options):
    with pytest.raises(ValueError):
        VirtualDriver(10, 10, ScreenMode.bw(), tmp_path, **options)


def test_gray_image_is_reduced_to_screen_levels(tmp_path):
    with VirtualDriver(10, 10, ScreenMode.gray(4), tmp_path) as display:
        display.write(Image.new("L", (10, 10), 100))
    assert {c for _, c in display.image.getcolors()} <= {0, 85, 170, 255}


def test_palette_screen_gets_only_its_colours(tmp_path):
    from PIL import ImageColor

    from epdlib import SEVEN_COLORS

    allowed = {ImageColor.getrgb(c) for c in SEVEN_COLORS}
    with VirtualDriver(10, 10, ScreenMode.palette(), tmp_path) as display:
        display.write(Image.new("RGB", (10, 10), (123, 45, 200)))
    assert {c for _, c in display.image.getcolors()} <= allowed


def test_fast_is_only_a_request(tmp_path):
    with VirtualDriver(10, 10, ScreenMode.bw(), tmp_path, fast_refresh=False) as display:
        display.write(Image.new("1", (10, 10)), fast=True)
    assert ("write", "full") in display.log


def test_converts_to_screen_mode(tmp_path):
    with VirtualDriver(10, 10, ScreenMode.gray(4), tmp_path) as display:
        display.write(Image.new("RGB", (10, 10), (100, 100, 100)))
    assert display.image.mode == "L"
    assert {c for _, c in display.image.getcolors()} <= {0, 85, 170, 255}


def test_old_files_are_removed(tmp_path):
    with VirtualDriver(10, 10, ScreenMode.bw(), tmp_path, keep=2) as display:
        for _ in range(4):
            display.write(Image.new("1", (10, 10)))
    assert sorted(p.name for p in tmp_path.glob("0*.png")) == ["0003.png", "0004.png"]


def test_clear(tmp_path):
    with VirtualDriver(10, 10, ScreenMode.palette(), tmp_path) as display:
        display.clear()
    assert display.image.getpixel((0, 0)) == (255, 255, 255)
