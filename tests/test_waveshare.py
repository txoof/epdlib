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
    with WaveshareDriver("epd7in5_V2", board=fake, timeout=0.5) as driver:
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


def test_fast_write_is_a_full_write(screen, fake):
    screen.write(page(), fast=True)
    assert len(fake.data_after(NEW_IMAGE)) == BYTES and REFRESH in fake.commands


def test_clear_makes_the_screen_white(screen, fake):
    screen.clear()
    assert fake.data_after(NEW_IMAGE) == bytes(BYTES)
    assert fake.data_after(OLD_IMAGE) == b"\xff" * BYTES


def test_sleep_switches_power_off_and_write_wakes(screen, fake):
    screen.sleep()
    assert fake.commands[-1] == DEEP_SLEEP and fake.pins[PWR_PIN] is False
    sent = len(fake.sent)
    screen.sleep()  # already asleep: nothing
    assert len(fake.sent) == sent
    screen.write(page())
    assert fake.commands.count(POWER_ON) == 2 and fake.pins[PWR_PIN] is True  # init again
    assert shown(fake.data_after(NEW_IMAGE)) == screen.check_image(page())


def test_clear_wakes_a_sleeping_screen(screen, fake):
    screen.sleep()
    screen.clear()
    assert fake.commands.count(POWER_ON) == 2 and fake.commands[-2:] == [REFRESH, 0x71]


def test_power_pin_none_leaves_gpio_18_alone(fake):
    with WaveshareDriver(power_pin=None, board=fake) as screen:
        screen.write(page())
        screen.sleep()
    assert PWR_PIN not in fake.outputs  # FakeBoard also fails on any write to it


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


def test_stuck_busy_pin_times_out_in_write(screen, fake):
    fake.busy_stuck = True
    with pytest.raises(DisplayTimeout):
        screen.write(page())
    fake.busy_stuck = False
    screen.init()  # starts again after a timeout
    screen.write(page())


def test_each_operation_gets_its_own_time_limit(screen, fake):
    time.sleep(0.6)  # longer than the 0.5 s limit, between operations
    screen.write(page())
    screen.clear()


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
    other = WaveshareDriver(board=FakeBoard())
    with pytest.raises(DisplayError, match="another Waveshare screen"):
        other.init()
    screen.write(page())  # the first one still works
    screen.close()
    other.init()
    other.close()


def test_wrong_image_size(screen):
    with pytest.raises(DisplayError, match="800x480"):
        screen.write(Image.new("L", (480, 800), 255))


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"model": "epd99in9"}, "unknown Waveshare model"),
        ({"power_pin": 12}, "power_pin"),
        ({"timeout": 0}, "timeout"),
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
