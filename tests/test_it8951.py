import time

import pytest
from PIL import Image, ImageDraw

from epdlib.drivers import DisplayError, DisplayTimeout
from epdlib.drivers.it8951 import MODELS, IT8951Driver, Mode
from tests.fake_it8951 import FakeIT8951

SIZE = (1200, 825)
FULL = (0, 0, *SIZE)


def page(text_at=(100, 100), gray=None):
    """A white page with a black square, and a gray one when ``gray`` is given."""
    image = Image.new("L", SIZE, 255)
    draw = ImageDraw.Draw(image)
    x, y = text_at
    draw.rectangle((x, y, x + 49, y + 49), fill=0)
    if gray is not None:
        draw.rectangle((*gray, gray[0] + 49, gray[1] + 49), fill=136)
    return image


def make(fake, **options):
    """A driver on the fake bus, without the reset pause, so tests run quickly."""
    options = {"vcom": -1.90, "ready_timeout": 0.05, "timeout": 0.5, **options}
    driver = IT8951Driver("9.7", bus=fake, **options)
    driver.reset_pulse = 0
    return driver


@pytest.fixture
def fake():
    return FakeIT8951()


@pytest.fixture
def screen(fake):
    with make(fake) as driver:
        yield driver


def test_init_sets_vcom_and_reads_device_info(screen, fake):
    assert fake.vcom == pytest.approx(-1.90)
    assert fake.registers[0x0004] == 1  # packed pixel mode
    assert (screen.firmware, screen.lut) == ("WS_v.0.2T1", "8M14T")
    assert not fake.in_reset and fake.resets == 1
    assert fake.command_hz == {IT8951Driver.cmd_hz}


def test_pixels_are_sent_at_data_speed(screen, fake):
    screen.write(page())
    assert fake.pixel_hz == {IT8951Driver.data_hz}
    assert fake.command_hz == {IT8951Driver.cmd_hz}


def test_vcom_not_taken_is_an_error(fake):
    fake.vcom_ignored = True
    with pytest.raises(DisplayError, match="VCOM"):
        make(fake).init()
    assert fake.closed == 1


def test_first_write_is_full_gc16(screen, fake):
    screen.write(page(), fast=True)
    assert fake.draws == [(*FULL, Mode.GC16)]
    assert fake.memory.tobytes() == page().tobytes()
    assert fake.registers[0x0208] == 0x3456 and fake.registers[0x020A] == 0x0012


def test_large_image_is_split_into_transfers_within_the_limit(fake):
    fake.block = 1000
    with make(fake) as screen:
        screen.write(page())  # the fake checks each transfer's size
    assert fake.memory.tobytes() == page().tobytes()


def test_pixel_order_within_a_byte(screen, fake):
    """Two pixels share a byte: a black pixel at an odd x must stay at that x."""
    image = Image.new("L", SIZE, 255)
    image.putpixel((101, 7), 0)
    image.putpixel((102, 7), 136)
    screen.write(image)
    assert [fake.memory.getpixel((x, 7)) for x in (100, 101, 102, 103)] == [255, 0, 136, 255]


def test_image_is_reduced_to_16_grays(screen, fake):
    screen.write(Image.new("RGB", SIZE, (102, 102, 102)))  # exactly gray level 6 of 16
    assert fake.memory.getextrema() == (102, 102)
    screen.write(Image.new("RGB", SIZE, (100, 100, 100)))  # between levels 5 and 6
    assert {v for _, v in fake.memory.getcolors()} == {85, 102}


def test_wrong_image_size_is_an_error(screen):
    with pytest.raises(DisplayError, match="screen is 1200x825"):
        screen.write(Image.new("L", (100, 100)))


def test_clear_uses_init(screen, fake):
    screen.write(page())
    screen.clear()
    assert fake.draws[-1] == (*FULL, Mode.INIT)
    assert fake.memory.getextrema() == (255, 255)


# ---------------------------------------------------------------------- fast writes


def test_fast_write_sends_only_the_changed_rectangle(screen, fake):
    screen.write(page((100, 100)))
    screen.write(page((102, 100)), fast=True)
    # changed pixels: x 100..151, widened to whole groups of 4 pixels: 100..152
    assert fake.draws[-1] == (100, 100, 52, 50, Mode.DU)
    assert fake.memory.tobytes() == page((102, 100)).tobytes()


def test_fast_write_with_gray_uses_gc16_on_that_rectangle(screen, fake):
    screen.write(page())
    screen.write(page(gray=(400, 400)), fast=True)
    assert fake.draws[-1] == (400, 400, 52, 50, Mode.GC16)


def test_gray_mode_can_be_changed(screen, fake):
    screen.fast_gray_mode = Mode.GL16
    screen.write(page())
    screen.write(page(gray=(400, 400)), fast=True)
    assert fake.draws[-1][-1] == Mode.GL16


def test_nothing_sent_when_nothing_changed(screen, fake):
    screen.write(page())
    screen.write(page(), fast=True)
    assert len(fake.draws) == 1


def test_full_write_when_not_fast(screen, fake):
    screen.write(page())
    screen.write(page((104, 100)))
    assert fake.draws[-1] == (*FULL, Mode.GC16)


@pytest.mark.parametrize("max_refresh, modes", [(2, "FFfFFfF"), (1, "FfFfFfF"), (0, "FFFFFFF")])
def test_max_refresh_forces_full_writes(fake, max_refresh, modes):
    """F = fast (area) write, f = forced full write. The first write is always full."""
    seen = ""
    with make(fake, max_refresh=max_refresh) as screen:
        screen.write(page((0, 0)))
        for n in range(1, len(modes) + 1):
            screen.write(page((4 * n, 0)), fast=True)
            seen += "f" if fake.draws[-1][:4] == FULL else "F"
    assert seen == modes


def test_after_clear_a_fast_write_is_an_area(screen, fake):
    screen.write(page())
    screen.clear()
    screen.write(page(), fast=True)
    assert fake.draws[-1] == (100, 100, 52, 50, Mode.DU)


def test_after_a_failed_write_the_next_write_is_full(screen, fake):
    screen.write(page())
    fake.busy_stuck = True
    with pytest.raises(DisplayTimeout):
        screen.write(page((104, 100)), fast=True)
    fake.busy_stuck = False
    screen.write(page((108, 100)), fast=True)
    assert fake.draws[-1] == (*FULL, Mode.GC16)


def test_unaligned_left_edge_rounds_down(screen, fake):
    screen.write(page((103, 100)))
    screen.write(page((105, 100)), fast=True)
    assert fake.draws[-1] == (100, 100, 56, 50, Mode.DU)
    assert fake.memory.tobytes() == page((105, 100)).tobytes()


def test_unchanged_gray_in_the_widened_edge_uses_gray_mode(screen, fake):
    """The columns added by rounding to 4 pixels are sent again, so their grays count."""
    old, new = page((102, 100)), page((104, 100))
    for image in (old, new):
        ImageDraw.Draw(image).rectangle((100, 100, 101, 149), fill=136)
    screen.write(old)
    screen.write(new, fast=True)
    assert fake.draws[-1] == (100, 100, 56, 50, Mode.GC16)


@pytest.mark.parametrize("level", [17, 238])
def test_near_black_and_near_white_count_as_gray(screen, fake, level):
    screen.write(page())
    image = page()
    ImageDraw.Draw(image).rectangle((400, 400, 449, 449), fill=level)
    screen.write(image, fast=True)
    assert fake.draws[-1][-1] == Mode.GC16


def test_unchanged_image_after_the_limit_sends_nothing(fake):
    with make(fake, max_refresh=1) as screen:
        screen.write(page((0, 0)))
        screen.write(page((4, 0)), fast=True)
        screen.write(page((4, 0)), fast=True)
        assert len(fake.draws) == 2
        screen.write(page((8, 0)), fast=True)  # the forced full write comes with the change
        assert fake.draws[-1][:4] == FULL


def test_unchanged_writes_do_not_count(fake):
    with make(fake, max_refresh=1) as screen:
        screen.write(page((0, 0)))
        screen.write(page((0, 0)), fast=True)
        screen.write(page((4, 0)), fast=True)
        assert fake.draws[-1][:4] != FULL


def test_clear_restarts_the_fast_count(fake):
    with make(fake, max_refresh=2) as screen:
        screen.write(page((0, 0)))
        screen.write(page((4, 0)), fast=True)
        screen.write(page((8, 0)), fast=True)
        screen.clear()
        screen.write(page((12, 0)), fast=True)
        assert fake.draws[-1][:4] != FULL


def test_after_close_and_init_the_next_write_is_full(screen, fake):
    screen.write(page())
    screen.close()
    screen.init()
    screen.write(page((104, 100)), fast=True)
    assert fake.draws[-1] == (*FULL, Mode.GC16)


def test_unknown_fast_gray_mode_is_refused(screen):
    screen.fast_gray_mode = 9
    screen.write(page())
    with pytest.raises(ValueError):
        screen.write(page(gray=(400, 400)), fast=True)


# ---------------------------------------------------------------------- settings


def test_vcom_is_required():
    with pytest.raises(ValueError, match="ribbon cable"):
        IT8951Driver("9.7")


@pytest.mark.parametrize(
    "options",
    [
        {"vcom": 1.0},
        {"vcom": -0.4},
        {"vcom": -3.1},
        {"vcom": -1.9, "max_refresh": -1},
        {"vcom": -1.9, "max_refresh": 2.5},
        {"vcom": -1.9, "max_refresh": True},
        {"vcom": -1.9, "timeout": 0},
        {"vcom": -1.9, "timeout": float("nan")},
        {"vcom": -1.9, "ready_timeout": 0},
        {"vcom": -1.9, "ready_timeout": float("nan")},
    ],
)
def test_bad_settings(options):
    with pytest.raises(ValueError):
        IT8951Driver("9.7", **options)


def test_unknown_model():
    with pytest.raises(ValueError, match="known: 6, 7.8, 9.7, 10.3"):
        IT8951Driver("13.3", vcom=-1.9)


def test_models_list_only_9_7_as_tested():
    assert [name for name, info in MODELS.items() if info.tested] == ["9.7"]
    assert all(info.mode.levels == 16 and info.fast_refresh for info in MODELS.values())


def test_wrong_model_is_found_at_init():
    fake = FakeIT8951(1872, 1404)
    driver = make(fake)
    with pytest.raises(DisplayError, match="reports 1872x1404.*check the selected model"):
        driver.init()
    assert fake.closed == 1


# ---------------------------------------------------------------------- faults


def test_no_answer_is_an_error_and_releases_the_bus():
    fake = FakeIT8951()
    fake.silent = True
    with pytest.raises(DisplayError, match="no answer"):
        make(fake).init()
    assert fake.closed == 1


def test_busy_line_stuck_times_out(screen, fake):
    fake.busy_stuck = True
    start = time.monotonic()
    with pytest.raises(DisplayTimeout, match="busy line"):
        screen.write(page())
    assert time.monotonic() - start < 0.3  # ready_timeout is 0.05 s


def test_busy_line_stuck_at_start_times_out_within_the_operation_limit(fake):
    """The wait after the reset may take up to 5 s, but never longer than ``timeout``."""
    fake.busy_stuck = True
    start = time.monotonic()
    with pytest.raises(DisplayTimeout, match="busy line"):
        make(fake, timeout=0.3).init()
    assert time.monotonic() - start < 1.0
    assert fake.closed == 1


def test_driver_waits_until_drawing_is_done(screen, fake):
    fake.draw_reads = 5
    screen.write(page())
    screen.write(page((104, 100)))
    assert fake._drawing == 0  # every "still drawing" answer was waited out


def test_redraw_that_never_ends_times_out(screen, fake):
    screen.write(page())
    fake.redraw_stuck = True
    start = time.monotonic()
    with pytest.raises(DisplayTimeout, match="did not finish drawing"):
        screen.write(page((104, 100)))
    assert time.monotonic() - start < 1.0  # timeout is 0.5 s


def test_close_releases_the_bus_once_and_is_safe_to_repeat(fake):
    driver = make(fake)
    with pytest.raises(RuntimeError), driver:
        raise RuntimeError("boom")
    driver.close()
    assert (fake.opened, fake.closed) == (1, 1)


def test_write_after_close_is_an_error(fake):
    driver = make(fake)
    driver.init()
    driver.close()
    with pytest.raises(DisplayError, match="closed"):
        driver.write(page(), fast=True)


def test_init_again_reopens_the_bus(screen, fake):
    screen.init()
    assert (fake.opened, fake.closed) == (2, 1)


def test_sleep_then_write_wakes_the_screen(screen, fake):
    screen.write(page())
    screen.sleep()
    assert fake.asleep
    screen.write(page((104, 100)))  # the fake refuses commands until SYS_RUN wakes it
    assert not fake.asleep
    assert fake.memory.tobytes() == page((104, 100)).tobytes()


def test_import_does_not_load_hardware_libraries():
    import subprocess
    import sys

    code = (
        "import sys, epdlib.drivers.it8951\nprint('spidev' in sys.modules, 'gpiod' in sys.modules)"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False False"
