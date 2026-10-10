import hashlib
import time
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from epdlib.drivers import DisplayError, DisplayTimeout
from epdlib.drivers.waveshare import MODELS, WaveshareDriver
from epdlib.drivers.waveshare.board import PWR_PIN
from epdlib.drivers.waveshare.vendor import epdconfig
from tests.fake_waveshare import FakeBoard

VENDOR = Path(epdconfig.__file__).parent
SIZE = (800, 480)
BYTES = 800 * 480 // 8

# Commands of the 7.5" V2's controller, as sent by Waveshare's epd7in5_V2.py
POWER_ON, OLD_IMAGE, REFRESH, NEW_IMAGE, DEEP_SLEEP = 0x04, 0x10, 0x12, 0x13, 0x07


@pytest.fixture(autouse=True)
def no_delays(monkeypatch):
    """Skip the model file's pauses (up to 2 s in sleep), so tests run quickly."""
    monkeypatch.setattr(epdconfig, "delay_ms", lambda ms: None)


@pytest.fixture
def fake():
    return FakeBoard()


@pytest.fixture
def screen(fake):
    with WaveshareDriver("epd7in5_V2", board=fake, timeout=0.2) as driver:
        yield driver


def page():
    image = Image.new("L", SIZE, 255)
    ImageDraw.Draw(image).rectangle((100, 100, 199, 149), fill=0)
    return image


def shown(data: bytes) -> Image.Image:
    """The image in a 1-bit screen buffer (the screen uses 1 for black, Pillow 0)."""
    return Image.frombytes("1", SIZE, bytes(b ^ 0xFF for b in data))


def git_fingerprint(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def test_waveshare_files_are_unchanged():
    lines = [ln.split() for ln in (VENDOR / "UPSTREAM.txt").read_text().splitlines()]
    listed = {name: sha for sha, name in (ln for ln in lines if ln and ln[0] != "#")}
    for name, sha in listed.items():
        assert git_fingerprint(VENDOR / name) == sha, f"{name} differs from Waveshare's file"
    assert {f"{m}.py" for m in MODELS} <= set(listed)
    copied = {p.name for p in VENDOR.glob("*.py")} - {"epdconfig.py", "__init__.py"}
    assert copied == set(listed), "every copied file must be listed in UPSTREAM.txt"


def test_init_switches_power_on_and_resets(screen, fake):
    assert fake.outputs == (17, 25, PWR_PIN) and fake.busy == 24
    assert fake.pins[PWR_PIN] is True
    assert fake.resets == 1
    assert POWER_ON in fake.commands


def test_write_sends_the_image(screen, fake):
    image = page()
    screen.write(image)
    assert shown(fake.data_after(NEW_IMAGE)) == screen.check_image(image)
    assert fake.commands[-2:] == [REFRESH, 0x71]  # refresh, then "busy?" until ready


def test_write_takes_1_bit_and_rgb_images(screen, fake):
    screen.write(page().convert("1"))
    first = fake.data_after(NEW_IMAGE)
    screen.write(page().convert("RGB"))
    assert fake.data_after(NEW_IMAGE) == first


# ---------------------------------------------------------------- fast writes


def moved(n: int) -> Image.Image:
    """The page with a second square moved ``n`` steps to the right."""
    image = page()
    ImageDraw.Draw(image).rectangle((300 + 20 * n, 300, 339 + 20 * n, 339), fill=0)
    return image


def kinds(fake, since: int) -> list[str]:
    """ "full" or "fast" for each refresh sent after ``fake.sent[since]``, by the init that
    set the screen up: Waveshare's init sends 0x06 0x17 ..., init_fast sends 0xE5 0x5A."""
    out, mode, last = [], None, None
    for i, (kind, data) in enumerate(fake.sent):
        if kind == "cmd":
            last = data[0]
        elif last == 0x06 and data[0] == 0x17:
            mode = "full"
        elif last == 0xE5 and data[0] == 0x5A:
            mode = "fast"
        if i >= since and kind == "cmd" and data[0] == REFRESH:
            out.append(mode)
    return out


def test_first_fast_write_is_full(screen, fake):
    screen.write(page(), fast=True)
    assert kinds(fake, 0) == ["full"]
    assert len(fake.data_after(NEW_IMAGE)) == BYTES and REFRESH in fake.commands


def test_fast_write_uses_waveshare_fast_refresh(screen, fake):
    screen.write(moved(0))
    start, starts = len(fake.sent), fake.commands.count(POWER_ON)
    screen.write(moved(1), fast=True)
    assert kinds(fake, start) == ["fast"]
    assert shown(fake.data_after(NEW_IMAGE)) == screen.check_image(moved(1))
    screen.write(moved(2), fast=True)  # still in fast mode: no second start-up
    assert fake.commands.count(POWER_ON) == starts + 1


def test_fast_write_of_an_unchanged_image_sends_nothing(screen, fake):
    screen.write(page())
    sent = len(fake.sent)
    screen.write(page(), fast=True)
    assert len(fake.sent) == sent


@pytest.mark.parametrize(
    ("max_refresh", "expected"),
    [
        (2, ["full", "fast", "fast", "full", "fast", "fast"]),
        (0, ["full", "fast", "fast", "fast", "fast", "fast"]),
    ],
)
def test_max_refresh(fake, max_refresh, expected):
    with WaveshareDriver(board=fake, max_refresh=max_refresh) as screen:
        for n in range(6):
            screen.write(moved(n), fast=True)
            screen.write(moved(n), fast=True)  # unchanged: does not count
    assert kinds(fake, 0) == expected


def test_full_write_after_fast_runs_the_normal_init(screen, fake):
    screen.write(moved(0))
    screen.write(moved(1), fast=True)
    starts = fake.commands.count(POWER_ON)
    screen.write(moved(2))
    assert fake.commands.count(POWER_ON) == starts + 1
    assert fake.data_after(0x06) == bytes([0x17, 0x17, 0x28, 0x17])  # init's first setting


def test_fast_write_after_sleep_and_clear(screen, fake):
    screen.write(moved(0))
    screen.sleep()
    start = len(fake.sent)
    screen.write(moved(1), fast=True)  # wakes in fast mode; the last image is known
    assert kinds(fake, start) == ["fast"]
    screen.clear()
    start = len(fake.sent)
    screen.write(moved(2), fast=True)
    assert kinds(fake, start) == ["fast"]


def test_fast_write_after_close_and_init_is_full(screen, fake):
    screen.write(moved(0))
    screen.close()
    screen.init()
    start = len(fake.sent)
    screen.write(moved(1), fast=True)
    assert kinds(fake, start) == ["full"]


def test_clear_starts_the_max_refresh_count_again(fake):
    with WaveshareDriver(board=fake, max_refresh=2) as screen:
        screen.write(moved(0))
        screen.write(moved(1), fast=True)
        screen.write(moved(2), fast=True)
        screen.clear()
        start = len(fake.sent)
        screen.write(moved(3), fast=True)
        screen.write(moved(4), fast=True)
    assert kinds(fake, start) == ["fast", "fast"]


def test_same_pixels_with_other_metadata_count_as_unchanged(screen, fake):
    image = screen.check_image(page())
    screen.write(image)
    sent = len(fake.sent)
    other = image.copy()
    other.info["dpi"] = (72, 72)  # e.g. read from a PNG file
    screen.write(other, fast=True)
    assert len(fake.sent) == sent


def test_drawing_on_the_written_image_afterwards_is_seen(screen, fake):
    image = screen.check_image(page())  # a 1-bit image: the driver gets this very object
    screen.write(image)
    ImageDraw.Draw(image).rectangle((500, 300, 549, 349), fill=0)
    sent = len(fake.sent)
    screen.write(image, fast=True)
    assert len(fake.sent) > sent


def test_sleep_after_waking_sleeps_again(screen, fake):
    screen.sleep()
    screen.write(page())
    screen.sleep()
    assert fake.commands.count(DEEP_SLEEP) == 2


@pytest.mark.timeout(5)
def test_failed_wake_still_lets_sleep_switch_the_power_off(screen, fake):
    screen.sleep()
    fake.busy_stuck = True
    with pytest.raises(DisplayTimeout):
        screen.write(page())  # init fails while waking
    fake.busy_stuck = False
    screen.sleep()
    assert fake.commands.count(DEEP_SLEEP) == 2 and fake.pins[PWR_PIN] is False


@pytest.mark.timeout(5)
def test_failed_fast_write_makes_the_next_write_full(screen, fake):
    screen.write(moved(0))
    fake.busy_stuck = True
    with pytest.raises(DisplayTimeout):
        screen.write(moved(1), fast=True)
    fake.busy_stuck = False
    start = len(fake.sent)
    screen.write(moved(1), fast=True)
    assert kinds(fake, start) == ["full"]


def test_clear_makes_the_screen_white(screen, fake):
    screen.clear()
    assert fake.data_after(NEW_IMAGE) == bytes(BYTES)
    assert fake.data_after(OLD_IMAGE) == b"\xff" * BYTES


def test_sleep_switches_power_off_and_write_wakes(screen, fake):
    screen.sleep()
    assert fake.commands[-1] == DEEP_SLEEP
    assert fake.pins == {17: False, 25: False, PWR_PIN: False}  # all outputs low
    sent = len(fake.sent)
    screen.sleep()  # already asleep: nothing
    assert len(fake.sent) == sent
    screen.write(page())
    assert fake.commands.count(POWER_ON) == 2 and fake.pins[PWR_PIN] is True  # init again
    assert shown(fake.data_after(NEW_IMAGE)) == screen.check_image(page())
    screen.write(page())  # awake now: no second start-up
    assert fake.commands.count(POWER_ON) == 2


def test_clear_wakes_a_sleeping_screen(screen, fake):
    screen.sleep()
    screen.clear()
    assert fake.commands.count(POWER_ON) == 2 and fake.commands[-2:] == [REFRESH, 0x71]


def test_power_pin_none_leaves_gpio_18_alone(fake):
    with WaveshareDriver(power_pin=None, board=fake) as screen:
        screen.write(page())
        screen.sleep()
        epdconfig.digital_write(PWR_PIN, 1)  # a model file switching power: ignored
    assert PWR_PIN not in fake.outputs  # FakeBoard also fails on any write to it


def test_screen_busy_for_a_while(screen, fake):
    fake.busy_for = 20
    screen.write(page())
    assert fake.busy_for == 0 and fake.commands[-21:] == [0x71] * 21


@pytest.mark.timeout(5)
def test_stuck_busy_pin_times_out_at_init_and_releases(fake):
    fake.busy_stuck = True
    driver = WaveshareDriver(board=fake, timeout=0.2)
    start = time.monotonic()
    with pytest.raises(DisplayTimeout, match="0.2 s"):
        driver.init()
    assert time.monotonic() - start < 1
    assert fake.closed == 1
    with pytest.raises(DisplayError, match="closed"):
        driver.write(page())


@pytest.mark.timeout(5)
def test_stuck_busy_pin_times_out_in_write_and_next_write_starts_again(screen, fake):
    fake.busy_stuck = True
    with pytest.raises(DisplayTimeout):
        screen.write(page())
    fake.busy_stuck = False
    screen.write(page())  # the screen's state is unknown: init runs first
    assert fake.commands.count(POWER_ON) == 2 and fake.resets == 2


@pytest.mark.timeout(5)
def test_failed_sleep_starts_the_screen_again_at_the_next_write(screen, fake):
    fake.busy_stuck = True
    with pytest.raises(DisplayTimeout):
        screen.sleep()
    fake.busy_stuck = False
    screen.sleep()  # counts as asleep: nothing sent
    screen.write(page())
    assert fake.commands.count(POWER_ON) == 2


def test_each_operation_gets_its_own_time_limit(screen, fake):
    time.sleep(0.3)  # longer than the 0.2 s limit, between operations
    screen.write(page())
    screen.clear()
    screen.sleep()


def test_busy_wait_does_not_spin(screen, fake, monkeypatch):
    pauses = []
    reads = fake.busy_reads
    monkeypatch.setattr(epdconfig.time, "sleep", pauses.append)
    screen.write(page())
    assert fake.busy_reads > reads and pauses.count(0.001) == fake.busy_reads - reads


def test_close_releases_and_can_repeat(fake):
    driver = WaveshareDriver(board=fake)
    driver.init()
    driver.close()
    driver.close()
    assert fake.closed == 1
    with pytest.raises(DisplayError, match="closed"):
        driver.clear()
    with pytest.raises(DisplayError, match="closed"):
        epdconfig.digital_write(17, 1)  # a model file called after close


def test_init_again_after_close(screen, fake):
    screen.close()
    screen.init()
    screen.write(page())
    assert fake.opened == 2 and fake.resets == 2


def test_only_one_screen_at_a_time(screen):
    second = FakeBoard()
    other = WaveshareDriver(board=second)
    with pytest.raises(DisplayError, match="another Waveshare screen"):
        other.init()
    assert second.opened == 0  # refused before claiming any pins
    screen.write(page())  # the first one still works
    screen.close()
    other.init()
    other.close()


def test_dropped_screen_does_not_block_the_next(fake):
    WaveshareDriver(board=FakeBoard()).init()  # never closed, then dropped
    with WaveshareDriver(board=fake) as screen:
        screen.write(page())


def test_model_init_failure_is_an_error(fake, monkeypatch):
    from epdlib.drivers.waveshare.vendor import epd7in5_V2

    monkeypatch.setattr(epd7in5_V2.EPD, "init", lambda self: -1)
    with pytest.raises(DisplayError, match=r"init\(\) failed"):
        WaveshareDriver(board=fake).init()
    assert fake.closed == 1


def test_wrong_image_size(screen):
    with pytest.raises(DisplayError, match="800x480"):
        screen.write(Image.new("L", (480, 800), 255))


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"model": "epd99in9"}, "unknown Waveshare model"),
        ({"power_pin": 12}, "power_pin"),
        ({"timeout": 0}, "timeout"),
        ({"max_refresh": -1}, "max_refresh"),
        ({"max_refresh": True}, "max_refresh"),
        ({"max_refresh": 1.5}, "max_refresh"),
    ],
)
def test_bad_settings(options, message):
    with pytest.raises(ValueError, match=message):
        WaveshareDriver(**options)


# ---------------------------------------------------------------- the helper file


def test_helper_masks_inverted_values(screen, fake):
    epdconfig.spi_writebyte([0x00, ~0x00, 0x0F, ~0x0F])  # Waveshare's display() sends ~byte
    assert fake.sent[-1][1] == b"\x00\xff\x0f\xf0"


def test_helper_refuses_or_ignores_what_it_does_not_have(screen):
    with pytest.raises(DisplayError, match="not supported"):
        epdconfig.digital_read(17)
    with pytest.raises(DisplayError, match="software SPI"):
        epdconfig.module_init(cleanup=True)
    epdconfig.digital_write(8, 0)  # chip select belongs to the kernel: ignored, not claimed
