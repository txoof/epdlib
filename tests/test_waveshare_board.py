"""GpioBoard with pretend ``gpiod`` and ``spidev`` modules, so it is tested without a Pi."""

import errno
import sys
import types
from enum import Enum

import pytest

from epdlib.drivers import DisplayError
from epdlib.drivers.waveshare.board import GpioBoard


class Value(Enum):
    ACTIVE = 1
    INACTIVE = 0


class FakeLines:
    def __init__(self, config):
        self.config = config
        self.values = {name: s.kw.get("output_value") for name, s in config.items()}
        self.released = 0

    def set_value(self, name, value):
        self.values[name] = value

    def get_value(self, name):
        return self.values[name]

    def release(self):
        self.released += 1


class FakeSpi:
    fail_open: type[BaseException] | None = None

    def __init__(self):
        self.sent, self.closed = [], 0

    def open(self, bus, device):
        if self.fail_open:
            raise self.fail_open(2, "No such file")
        self.opened = (bus, device)

    def writebytes2(self, data):
        self.sent.append(bytes(data))

    def close(self):
        self.closed += 1


@pytest.fixture
def hw(monkeypatch):
    """Install pretend gpiod/spidev; returns a namespace with what they recorded."""
    rec = types.SimpleNamespace(lines=None, spi=None, chip_pins={"GPIO17", "GPIO24", "GPIO25"})
    rec.request_error = None
    rec.chip_error = None

    class Chip:
        def __init__(self, path):
            if rec.chip_error:
                raise rec.chip_error

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def line_offset_from_id(self, name):
            if name not in rec.chip_pins:
                raise ValueError(name)

    class LineSettings:
        def __init__(self, **kw):
            self.kw = kw

    def request_lines(chip, consumer, config):
        if rec.request_error:
            raise rec.request_error
        rec.lines = FakeLines(config)
        return rec.lines

    def make_spi():
        rec.spi = FakeSpi()
        return rec.spi

    line = types.ModuleType("gpiod.line")
    line.Value = Value
    line.Direction = Enum("Direction", "INPUT OUTPUT")
    line.Bias = Enum("Bias", "PULL_DOWN PULL_UP")
    gpiod = types.ModuleType("gpiod")
    gpiod.Chip, gpiod.LineSettings, gpiod.request_lines, gpiod.line = (
        Chip,
        LineSettings,
        request_lines,
        line,
    )
    spidev = types.ModuleType("spidev")
    spidev.SpiDev = make_spi
    monkeypatch.setitem(sys.modules, "gpiod", gpiod)
    monkeypatch.setitem(sys.modules, "gpiod.line", line)
    monkeypatch.setitem(sys.modules, "spidev", spidev)
    monkeypatch.setattr(FakeSpi, "fail_open", None)
    return rec


def test_pins_spi_and_close(hw):
    board = GpioBoard((17, 25), 24)
    cfg = hw.lines.config
    assert cfg["GPIO17"].kw["output_value"] == Value.INACTIVE  # outputs start low
    assert cfg["GPIO24"].kw["bias"].name == "PULL_DOWN"
    assert (hw.spi.opened, hw.spi.mode, hw.spi.max_speed_hz) == ((0, 0), 0, 4_000_000)
    board.write_pin(17, True)
    assert hw.lines.values["GPIO17"] == Value.ACTIVE
    board.write_pin(17, False)
    assert hw.lines.values["GPIO17"] == Value.INACTIVE
    hw.lines.values["GPIO24"] = Value.ACTIVE
    assert board.read_pin(24) is True
    board.spi_write(b"\x01\x02")
    assert hw.spi.sent == [b"\x01\x02"]
    board.close()
    board.close()
    assert (hw.spi.closed, hw.lines.released) == (1, 1)


def test_not_a_pi(hw):
    with pytest.raises(DisplayError, match="does not look like a Raspberry Pi"):
        GpioBoard((17, 18), 24)  # this chip has no GPIO18


@pytest.mark.parametrize(
    ("where", "error", "message"),
    [
        ("chip", PermissionError(errno.EACCES, "denied"), "no permission .* gpio and spi groups"),
        ("request", OSError(errno.EBUSY, "busy"), "another program is using them"),
        ("request", OSError(errno.EINVAL, "bad"), r"cannot claim .*: \[Errno 22\] bad"),
    ],
)
def test_pin_errors(hw, where, error, message):
    setattr(hw, f"{where}_error", error)
    with pytest.raises(DisplayError, match=message):
        GpioBoard((17, 25), 24)


@pytest.mark.parametrize(
    ("error", "message"),
    [(FileNotFoundError, "spidev0.0 is missing: turn on SPI"), (PermissionError, "no permission")],
)
def test_spi_errors_release_the_pins(hw, monkeypatch, error, message):
    monkeypatch.setattr(FakeSpi, "fail_open", error)
    with pytest.raises(DisplayError, match=message):
        GpioBoard((17, 25), 24)
    assert hw.lines.released == 1
