"""Driver for e-paper screens with the IT8951 controller (Waveshare's IT8951 HAT).

Needs the optional pin and SPI libraries (the ``it8951`` install group, see
``docs/it8951.md``). Example::

    from epdlib.drivers.it8951 import IT8951Driver

    with IT8951Driver("9.7", vcom=-1.90) as screen:
        screen.write(image)  # full refresh (GC16)

How the controller talks over SPI: every transfer starts with a 2-byte "preamble" that
says what follows (a command, data to write, or data to read), then 16-bit words, most
significant byte first. Before each transfer the driver waits until the busy line is high.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from enum import IntEnum

from PIL import Image

from ...modes import ScreenMode
from .. import DisplayError, DisplayInfo, DisplayTimeout, Driver
from .bus import Bus, SpiBus

__all__ = ["MODELS", "VCOM_RANGE", "IT8951Driver", "Mode"]


class Mode(IntEnum):
    """Refresh modes, as numbered by the controller's waveform table.

    The numbers of the other modes (A2, GL16, ...) differ between screens; these three are
    the same on all of them.
    """

    INIT = 0  # long flash to white: removes all leftovers of earlier images
    DU = 1  # fast, black and white only, no flash
    GC16 = 2  # 16 grays with a flash: the full refresh


def _model(name: str, width: int, height: int, tested: bool = False) -> DisplayInfo:
    return DisplayInfo(
        model=f'Waveshare {name}" IT8951',
        width=width,
        height=height,
        mode=ScreenMode.gray(16),
        fast_refresh=False,
        tested=tested,
    )


#: Screens sold with Waveshare's IT8951 board, by size in inches. The 7.8" and 10.3"
#: have the same size in pixels, so :meth:`IT8951Driver.init` cannot tell them apart.
MODELS: dict[str, DisplayInfo] = {
    "6": _model("6", 800, 600),
    "7.8": _model("7.8", 1872, 1404),
    "9.7": _model("9.7", 1200, 825, tested=True),
    "10.3": _model("10.3", 1872, 1404),
}

# Preambles
_CMD = 0x6000
_WRITE = 0x0000
_READ = 0x1000

# Commands
_SYS_RUN = 0x0001
_SLEEP = 0x0003
_REG_RD = 0x0010
_REG_WR = 0x0011
_LD_IMG_AREA = 0x0021
_LD_IMG_END = 0x0022
_DPY_AREA = 0x0034
_VCOM = 0x0039
_GET_DEV_INFO = 0x0302

# Registers
_I80CPCR = 0x0004  # 1 = packed pixel mode
_LISAR = 0x0208  # image buffer address (low word; high word at +2)
_LUTAFSR = 0x1224  # not zero while the controller is still redrawing

#: VCOM values accepted, in volts. Waveshare's screens are printed with values in this range.
VCOM_RANGE = (-3.0, -0.5)

# Image loading: big-endian words, 4 bits per pixel, no rotation
_LOAD_4BPP = (1 << 8) | (2 << 4)

# Two pixels per byte, the first one in the high half.
_HIGH = bytes(p & 0xF0 for p in range(256))
_LOW = bytes(p >> 4 for p in range(256))


class IT8951Driver(Driver):
    """One IT8951 screen.

    - ``model``: a key of :data:`MODELS`, e.g. ``"9.7"``. :meth:`init` checks that the
      controller reports this model's size.
    - ``vcom``: the voltage printed on the screen's ribbon cable, e.g. ``-1.90``. Each
      screen has its own; a wrong value gives poor contrast. Required, between -3.0 and
      -0.5 (:data:`VCOM_RANGE`).
    - ``timeout``: the longest one operation (init, write, clear) may take, in seconds.
    - ``ready_timeout``: the longest one wait for the busy line may take, in seconds.
      Only the wait after the reset in :meth:`init` may take up to 5 s.

    ``fast`` is not supported yet: every write is a full refresh (GC16).
    """

    #: How long the reset line is held low in :meth:`init`, in seconds.
    reset_pulse = 0.1
    cmd_hz = 12_000_000
    data_hz = 24_000_000

    def __init__(
        self,
        model: str = "9.7",
        *,
        vcom: float | None = None,
        timeout: float = 15.0,
        ready_timeout: float = 2.0,
        bus: Callable[[], Bus] = SpiBus,
    ):
        super().__init__(timeout=timeout)
        if model not in MODELS:
            raise ValueError(f"unknown IT8951 model {model!r}; known: {', '.join(MODELS)}")
        if vcom is None:
            raise ValueError(
                "vcom is not set: use the value printed on the screen's ribbon cable, "
                "for example -1.90"
            )
        low, high = VCOM_RANGE
        if not low <= vcom <= high:
            raise ValueError(f"vcom must be between {low} and {high} volts, got {vcom}")
        if not (math.isfinite(ready_timeout) and ready_timeout > 0):
            raise ValueError("ready_timeout must be above zero")
        self.info = MODELS[model]
        self.vcom = vcom
        self.ready_timeout = ready_timeout
        self._make_bus = bus
        self._bus: Bus | None = None
        self._deadline = 0.0
        self._img_addr = 0
        #: Firmware and waveform table names the controller reported in :meth:`init`.
        self.firmware = ""
        self.lut = ""

    # ------------------------------------------------------------------ interface

    def init(self) -> None:
        self.close()
        self._start()
        try:
            self._bus = self._make_bus()
            self._reset()
            width, height = self._read_info()
            if (width, height) != (self.info.width, self.info.height):
                raise DisplayError(
                    f"the controller reports {width}x{height}, but {self.info.model} is "
                    f"{self.info.width}x{self.info.height}: check the selected model"
                )
            self._write_reg(_I80CPCR, 1)
            millivolts = round(-self.vcom * 1000)
            self._command(_VCOM, 1, millivolts)
            self._command(_VCOM, 0)
            if self._read_words(1)[0] != millivolts:
                raise DisplayError("the controller did not take the VCOM setting")
        except BaseException:
            self.close()
            raise

    def write(self, image: Image.Image, *, fast: bool = False) -> None:
        image = self.check_image(image)
        self._start()
        self._show(image, 0, 0, Mode.GC16)

    def clear(self) -> None:
        self._start()
        size = (self.info.width, self.info.height)
        self._show(Image.new("L", size, 255), 0, 0, Mode.INIT)

    def sleep(self) -> None:
        if self._bus is not None:
            self._start()
            self._command(_SLEEP)

    def close(self) -> None:
        bus, self._bus = self._bus, None
        if bus is not None:
            bus.close()

    # ------------------------------------------------------------------ drawing

    def _show(self, image: Image.Image, x: int, y: int, mode: Mode) -> None:
        """Load ``image`` into the controller at (x, y) and draw that area in ``mode``."""
        if self._bus is None:
            raise DisplayError("screen is closed: call init() first")
        w, h = image.size
        self._command(_SYS_RUN)
        self._wait_redraw()
        self._write_reg(_LISAR + 2, self._img_addr >> 16)
        self._write_reg(_LISAR, self._img_addr & 0xFFFF)
        self._command(_LD_IMG_AREA, _LOAD_4BPP, x, y, w, h)
        self._send_pixels(_pack(image))
        self._command(_LD_IMG_END)
        self._command(_DPY_AREA, x, y, w, h, int(mode))
        self._wait_redraw()

    def _send_pixels(self, packed: bytes) -> None:
        step = (self._bus.block - 2) // 2 * 2  # whole 16-bit words per transfer
        preamble = _WRITE.to_bytes(2, "big")
        for start in range(0, len(packed), step):
            self._wait_ready()
            self._bus.write(preamble + packed[start : start + step], self.data_hz)

    # ------------------------------------------------------------------ low level

    def _start(self) -> None:
        """Start the time limit for one operation."""
        self._deadline = time.monotonic() + self.timeout

    def _reset(self) -> None:
        self._bus.set_reset(True)
        time.sleep(self.reset_pulse)
        self._bus.set_reset(False)
        self._wait_ready(5.0)

    def _wait_ready(self, limit: float | None = None) -> None:
        """Wait until the busy line is high, within the wait's and the operation's limit."""
        deadline = min(time.monotonic() + (limit or self.ready_timeout), self._deadline)
        while not self._bus.ready():
            if time.monotonic() > deadline:
                raise DisplayTimeout("screen not ready: the busy line stayed low")
            time.sleep(0.0002)

    def _wait_redraw(self) -> None:
        """Wait until the controller has finished drawing."""
        while self._read_reg(_LUTAFSR):
            if time.monotonic() > self._deadline:
                raise DisplayTimeout(f"screen did not finish drawing within {self.timeout} s")
            time.sleep(0.005)

    def _transfer(self, data: bytes, hz: int | None = None) -> bytes:
        self._wait_ready()
        return self._bus.transfer(data, hz or self.cmd_hz)

    def _command(self, cmd: int, *args: int) -> None:
        self._transfer(_words(_CMD, cmd))
        for arg in args:
            self._transfer(_words(_WRITE, arg))

    def _read_words(self, count: int) -> list[int]:
        # preamble, 2 dummy bytes, then the data
        rx = self._transfer(_words(_READ) + bytes(2 + 2 * count))[4:]
        return [int.from_bytes(rx[i : i + 2], "big") for i in range(0, 2 * count, 2)]

    def _read_reg(self, reg: int) -> int:
        self._command(_REG_RD, reg)
        return self._read_words(1)[0]

    def _write_reg(self, reg: int, value: int) -> None:
        self._command(_REG_WR, reg, value)

    def _read_info(self) -> tuple[int, int]:
        self._command(_GET_DEV_INFO)
        w = self._read_words(20)
        if not any(w):
            raise DisplayError("no answer from the screen: check the cable and the HAT")
        self._img_addr = (w[3] << 16) | w[2]
        self.firmware = _text(w[4:12])
        self.lut = _text(w[12:20])
        return w[0], w[1]


def _words(preamble: int, *words: int) -> bytes:
    return b"".join(v.to_bytes(2, "big") for v in (preamble, *words))


def _text(words: list[int]) -> str:
    raw = b"".join(w.to_bytes(2, "big") for w in words)
    return raw.split(b"\x00")[0].decode("ascii", "replace")


def _pack(image: Image.Image) -> bytes:
    """Pack a gray image into 4 bits per pixel, two pixels per byte.

    Byte-table lookups and one big-integer OR, instead of a Python loop per pixel, so a
    full screen packs quickly without numpy.
    """
    raw = image.tobytes()
    if len(raw) % 2:
        raw += b"\xff"
    hi = raw[0::2].translate(_HIGH)
    lo = raw[1::2].translate(_LOW)
    return (int.from_bytes(hi, "big") | int.from_bytes(lo, "big")).to_bytes(len(hi), "big")
