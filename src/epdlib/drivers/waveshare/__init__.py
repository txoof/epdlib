"""Driver for Waveshare's small e-paper screens (the ones without the IT8951 controller).

Needs the optional pin and SPI libraries (the ``waveshare`` install group, see
``docs/waveshare.md``). Example::

    from epdlib.drivers.waveshare import WaveshareDriver

    with WaveshareDriver("epd7in5_V2") as screen:
        screen.write(image)
        screen.sleep()

Waveshare's own file for each screen model is used, copied unchanged into the ``vendor``
folder (``vendor/UPSTREAM.txt`` says from where). Only Waveshare's shared helper file,
``epdconfig.py``, is replaced by epdlib's own (``vendor/epdconfig.py``), which adds the
time limits and uses ``gpiod`` and ``spidev``. This driver calls the model file's
functions; their names differ between models, so each model has a row in a table here.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from types import ModuleType

from PIL import Image, ImageChops

from ...modes import ScreenMode
from .. import DisplayError, DisplayInfo, Driver
from .board import BUSY_PIN, DC_PIN, PWR_PIN, RST_PIN, Board, GpioBoard
from .vendor import epdconfig

__all__ = ["MODELS", "NOT_WORKING", "WaveshareDriver"]


@dataclass(frozen=True)
class _Calls:
    """How the driver calls one model's Waveshare file.

    - ``file``: the Waveshare file whose code is used, if not the model's own.
    - ``init``, ``buffer``, ``display``, ``clear``, ``sleep``: names of the file's
      functions. ``init_args`` and ``clear_args`` are passed to them; a string there names
      a value of the file's ``EPD`` object (for example ``"lut_full_update"``).
    - ``layers``: 2 for three-colour screens, whose ``display`` takes a black layer and a
      colour layer. The colour layer is sent empty (white): only black and white are
      supported on them for now (issue #96).
    - ``fast_init`` and ``fast``: for fast writes, the model's init for its fast mode, and
      a function ``(epd, buffer)`` that shows a buffer in that mode. ``None``: the model
      has no fast mode, and every write is full.
    """

    file: str | None = None
    init: str = "init"
    init_args: tuple = ()
    buffer: str = "getbuffer"
    display: str = "display"
    clear: str = "Clear"
    clear_args: tuple = ()
    sleep: str = "sleep"
    layers: int = 1
    fast_init: str | None = None
    fast: Callable | None = None


def _display(epd, buffer) -> None:
    epd.display(buffer)


_FULL = _Calls()
_LUT = _Calls(init_args=("lut_full_update",))
_TWO = _Calls(layers=2)

_BW = ScreenMode.bw()
# Waveshare's exact colours: their files match pixels to these values.
_FOUR = ScreenMode.palette(("#000000", "#ffffff", "#ffff00", "#ff0000"))
_SIX = ScreenMode.palette(("#000000", "#ffffff", "#ffff00", "#ff0000", "#0000ff", "#00ff00"))
_SEVEN = ScreenMode.palette(
    ("#000000", "#ffffff", "#00ff00", "#0000ff", "#ff0000", "#ffff00", "#ff8000")
)

# Every model: (width, height, mode, calls). Sizes are Waveshare's, wide side first;
# Waveshare's files turn an image of a tall screen themselves. Only full writes, except
# on tested models: a fast mode is added when it has been tried on the screen.
_TABLE: dict[str, tuple[int, int, ScreenMode, _Calls]] = {
    # Black and white
    "epd1in02": (128, 80, _BW, _Calls(init="Init", sleep="Sleep")),
    "epd1in54": (200, 200, _BW, _LUT),
    "epd1in54_V2": (200, 200, _BW, _Calls(init_args=(False,))),
    "epd2in13": (250, 122, _BW, _LUT),
    "epd2in13_V2": (250, 122, _BW, _Calls(init_args=("FULL_UPDATE",))),
    "epd2in13_V3": (250, 122, _BW, _FULL),
    "epd2in13_V4": (250, 122, _BW, _FULL),
    "epd2in13d": (212, 104, _BW, _FULL),
    "epd2in66": (296, 152, _BW, _Calls(init_args=(0,))),
    "epd2in7": (264, 176, _BW, _FULL),
    "epd2in7_V2": (264, 176, _BW, _FULL),
    "epd2in9": (296, 128, _BW, _LUT),
    "epd2in9_V2": (296, 128, _BW, _FULL),
    "epd2in9_V3": (296, 128, _BW, _FULL),
    "epd2in9d": (296, 128, _BW, _FULL),
    "epd3in52": (360, 240, _BW, _FULL),
    # 3.7": init mode 1 is black and white (0 is 4 grays)
    "epd3in7": (
        480,
        280,
        _BW,
        _Calls(init_args=(1,), display="display_1Gray", clear_args=(0xFF, 1)),
    ),
    "epd4in2": (400, 300, _BW, _FULL),
    "epd4in2_V2": (400, 300, _BW, _FULL),
    "epd4in26": (800, 480, _BW, _FULL),
    "epd5in79": (792, 272, _BW, _FULL),
    "epd5in83": (600, 448, _BW, _FULL),
    "epd5in83_V2": (648, 480, _BW, _FULL),
    "epd7in5": (640, 384, _BW, _FULL),
    "epd7in5_HD": (880, 528, _BW, _FULL),
    "epd7in5_V2": (800, 480, _BW, _Calls(fast_init="init_fast", fast=_display)),
    "epd7in5_V2_old": (800, 480, _BW, _FULL),
    "epd13in3k": (960, 680, _BW, _FULL),
    # Three colours (black, white, red or yellow): black and white only for now
    "epd1in54b": (200, 200, _BW, _TWO),
    "epd1in54b_V2": (200, 200, _BW, _TWO),
    "epd1in54c": (152, 152, _BW, _TWO),
    "epd2in13b_V3": (212, 104, _BW, _TWO),
    "epd2in13b_V4": (250, 122, _BW, _TWO),
    "epd2in13bc": (212, 104, _BW, _TWO),
    "epd2in15b": (296, 160, _BW, _TWO),
    "epd2in66b": (296, 152, _BW, _TWO),
    # The 2.7" B with the 2.7" black-and-white file: with epdlib 0.6 this was much faster
    # than its own file with an empty red layer (txoof's screen; not tried with this driver).
    "epd2in7b": (264, 176, _BW, _Calls(file="epd2in7")),
    "epd2in7b_V2": (264, 176, _BW, _TWO),
    "epd2in9b_V3": (296, 128, _BW, _TWO),
    "epd2in9b_V4": (296, 128, _BW, _TWO),
    "epd2in9bc": (296, 128, _BW, _TWO),
    "epd4in2bc": (400, 300, _BW, _TWO),
    "epd5in79b": (792, 272, _BW, _TWO),
    "epd5in83b_V2": (648, 480, _BW, _TWO),
    "epd5in83bc": (600, 448, _BW, _TWO),
    "epd7in5b_HD": (880, 528, _BW, _TWO),
    "epd7in5b_V2": (800, 480, _BW, _TWO),
    "epd7in5b_V2_old": (800, 480, _BW, _TWO),
    "epd7in5bc": (640, 384, _BW, _TWO),
    "epd13in3b": (960, 680, _BW, _TWO),
    # Four colours: black, white, yellow, red
    "epd1in64g": (168, 168, _FOUR, _FULL),
    "epd2in13g": (250, 122, _FOUR, _FULL),
    "epd2in15g": (296, 160, _FOUR, _FULL),
    "epd2in36g": (296, 168, _FOUR, _FULL),
    "epd2in66g": (360, 184, _FOUR, _FULL),
    "epd3in0g": (400, 168, _FOUR, _FULL),
    "epd4in37g": (512, 368, _FOUR, _FULL),
    "epd5in79g": (792, 272, _FOUR, _FULL),
    "epd7in3g": (800, 480, _FOUR, _FULL),
    # Six and seven colours
    "epd4in01f": (640, 400, _SEVEN, _FULL),
    "epd5in65f": (600, 448, _SEVEN, _FULL),
    "epd7in3e": (800, 480, _SIX, _FULL),
    "epd7in3f": (800, 480, _SEVEN, _FULL),
}

#: Waveshare files that do not work with epdlib, and why. A test checks that every copied
#: file is either here or used for a model.
NOT_WORKING: dict[str, str] = {
    file: "it sends data through Waveshare's own compiled helper (software SPI), which "
    "epdlib does not have"
    for file in ("epd4in2b_V2", "epd4in2b_V2_old")
}

#: Models run on a real screen (see docs/waveshare.md).
_TESTED = {"epd5in65f", "epd5in83", "epd7in5_V2"}

_CALLS = {file: row[3] for file, row in _TABLE.items()}


def _name(file: str) -> str:
    """Waveshare's name for a model: "epd2in13bc" -> '2.13" B/C', "epd7in5b_V2_old" ->
    '7.5" B V2 (old)'."""
    first, *rest = file.split("_")
    whole, rest_of_size = first[3:].split("in")
    fraction = rest_of_size.rstrip("abcdefghijklmnopqrstuvwxyz")
    letters = rest_of_size[len(fraction) :]
    parts = [f'{whole}.{fraction}"', "/".join(letters.upper())]
    parts += ["(old)" if part == "old" else part for part in rest]
    return " ".join(p for p in parts if p)


def _model(file: str) -> DisplayInfo:
    width, height, mode, calls = _TABLE[file]
    name = _name(file) + (" (black and white only)" if calls.layers == 2 or calls.file else "")
    return DisplayInfo(
        model=f"Waveshare {name}",
        width=width,
        height=height,
        mode=mode,
        fast_refresh=calls.fast is not None,
        tested=file in _TESTED,
    )


#: Supported screens, by the name of Waveshare's file for them (without ``.py``).
MODELS: dict[str, DisplayInfo] = {file: _model(file) for file in _TABLE}

# Some Waveshare files import a library they never use: RPi.GPIO (not installed with
# epdlib, and fails on the Pi 5) and distutils (gone in Python 3.12). Empty stand-ins are
# put in place of a missing one while such a file loads.
_UNUSED_IMPORTS = {"RPi.GPIO": {}, "distutils.command.build_scripts": {"build_scripts": None}}


@contextmanager
def _stand_ins():
    added = []
    for name, values in _UNUSED_IMPORTS.items():
        try:
            importlib.import_module(name)
        except Exception:  # missing, or fails on this computer
            parts = name.split(".")
            for i in range(1, len(parts) + 1):
                part = ".".join(parts[:i])
                if part not in sys.modules:
                    sys.modules[part] = ModuleType(part)
                    added.append(part)
            vars(sys.modules[name]).update(values)
    try:
        yield
    finally:
        for part in added:
            del sys.modules[part]


class WaveshareDriver(Driver):
    """One Waveshare screen.

    - ``model``: a key of :data:`MODELS`, the name of Waveshare's file for the screen,
      e.g. ``"epd7in5_V2"``.
    - ``power_pin``: GPIO 18, which switches the screen's power on newer Waveshare HATs
      (default), or ``None`` to leave GPIO 18 alone, for example for a HiFiBerry sound
      card, which also needs it. Other pins are not supported yet.
    - ``max_refresh``: after this many fast writes in a row, the next write is a full
      one. Fast writes refresh the whole screen too, but more briefly, so faint traces of
      earlier images can build up; a full write removes most of them. Default 4
      (recommended); 0 means never force a full write: then call :meth:`clear` or a full
      :meth:`write` yourself now and then. Ignored on models without a fast mode.
    - ``timeout``: the longest one operation (init, write, clear, sleep) may take, in
      seconds.

    A fast write of an image with the same pixels as the screen sends nothing. The first
    write after :meth:`init` or an error is always full, because the driver then does
    not know what the screen shows.

    Only one Waveshare screen can be open at a time in one program.
    """

    def __init__(
        self,
        model: str = "epd7in5_V2",
        *,
        power_pin: int | None = PWR_PIN,
        max_refresh: int = 4,
        timeout: float = 60.0,
        board: Callable[..., Board] = GpioBoard,
    ):
        super().__init__(timeout=timeout)
        if model in NOT_WORKING:
            raise ValueError(
                f"Waveshare model {model!r} does not work with epdlib: {NOT_WORKING[model]}"
            )
        if model not in MODELS:
            raise ValueError(f"unknown Waveshare model {model!r}; known: {', '.join(MODELS)}")
        if power_pin not in (PWR_PIN, None):
            raise ValueError(f"power_pin must be {PWR_PIN} or None, got {power_pin!r}")
        if isinstance(max_refresh, bool) or not isinstance(max_refresh, int) or max_refresh < 0:
            raise ValueError(f"max_refresh must be a whole number of 0 or more, got {max_refresh}")
        self.info = MODELS[model]
        self.model = model
        self.power_pin = power_pin
        self.max_refresh = max_refresh
        self._calls = _CALLS[model]
        self._make_board = board
        self._board: Board | None = None
        self._epd = None
        #: The screen was put to sleep (and its power switched off) and not woken since.
        self._asleep = False
        #: The model's init function that last ran, so the screen is set up for that mode;
        #: None after sleep, or after an operation failed part way and left the screen in
        #: an unknown state. The next write or clear then runs an init first.
        self._started: str | None = None
        #: What the screen shows now, or None when unknown (then the next write is full).
        self._shown: Image.Image | None = None
        self._fast_in_row = 0
        #: An empty colour layer for three-colour screens, made at the first write.
        self._blank: object | None = None

    # ------------------------------------------------------------------ interface

    def init(self) -> None:
        self.close()
        epdconfig.start(self.timeout)
        try:
            epdconfig.claim(self, power_pin=self.power_pin is not None)
            outputs = (RST_PIN, DC_PIN) + ((PWR_PIN,) if self.power_pin is not None else ())
            self._board = self._make_board(outputs, BUSY_PIN)
            epdconfig.connect(self, self._board)
            self._epd = self._module().EPD()
            self._start(self._calls.init)
        except BaseException:
            self.close()
            raise

    def write(self, image: Image.Image, *, fast: bool = False) -> None:
        image = self.check_image(image)
        if image.mode == "1":
            # Pillow keeps a white pixel set to 1 as 1, not 255, and some Waveshare files
            # take values below 64 as black: make white 255.
            image = image.point(lambda v: 255 if v else 0)
        self._begin()
        calls = self._calls
        if fast and calls.fast is not None and self._shown is not None:
            if ImageChops.difference(self._shown, image).getbbox() is None:
                return  # same pixels as on the screen: nothing is sent
            fast = not (self.max_refresh and self._fast_in_row >= self.max_refresh)
        else:
            fast = False
        self._start(calls.fast_init if fast else calls.init)
        buffers = [getattr(self._epd, calls.buffer)(image)]
        if calls.layers == 2:
            if self._blank is None:
                white = Image.new("1", image.size, 255)
                self._blank = getattr(self._epd, calls.buffer)(white)
            buffers.append(self._blank)
        self._shown = None  # unknown until the write has finished
        if fast:
            self._guard(calls.fast, self._epd, *buffers)
        else:
            self._guard(self._call, calls.display, *buffers)
        self._shown = image.copy()
        self._fast_in_row = self._fast_in_row + 1 if fast else 0

    def clear(self) -> None:
        self._begin()
        self._start(self._calls.init)
        self._shown = None
        self._guard(self._call, self._calls.clear, *self._calls.clear_args)
        self._shown = Image.new(self.info.mode.pil_mode, (self.info.width, self.info.height), 255)
        self._fast_in_row = 0

    def sleep(self) -> None:
        """Put the screen into deep sleep and switch its power off; the next write or clear
        wakes it. Calling it again while the screen sleeps does nothing."""
        if self._epd is not None and not self._asleep:
            epdconfig.start(self.timeout)
            # Set first: if sleep fails part way, the screen may be off already.
            self._asleep, self._started = True, None
            getattr(self._epd, self._calls.sleep)()

    def close(self) -> None:
        board, self._board = self._board, None
        self._epd = None
        self._asleep, self._started, self._shown = False, None, None
        epdconfig.detach(self)
        if board is not None:
            board.close()

    # ------------------------------------------------------------------ helpers

    def _module(self) -> ModuleType:
        with _stand_ins():
            return importlib.import_module(f"{__name__}.vendor.{self._calls.file or self.model}")

    def _begin(self) -> None:
        """Check the screen is open and start the operation's time limit."""
        if self._epd is None:
            raise DisplayError("screen is closed: call init() first")
        epdconfig.start(self.timeout)

    def _start(self, init: str) -> None:
        """Run the model's ``init`` function (each starts with a reset) unless it is the one
        the screen was last set up with: wakes a sleeping screen and switches modes."""
        if self._started != init:
            # Not asleep any more even if init fails: it may have switched the power on,
            # so the next sleep() must run.
            self._started, self._asleep = None, False
            # Power on first: most inits do it themselves, but the 13.3" files only when
            # the EPD object is made, so they would not wake from sleep.
            self._guard(epdconfig.module_init)
            args = self._calls.init_args if init == self._calls.init else ()
            args = [getattr(self._epd, a) if isinstance(a, str) else a for a in args]
            self._guard(self._call, init, *args)
            self._started = init

    def _guard(self, call: Callable, *args) -> None:
        """Run ``call``; if it fails, the screen's state is unknown, so the next write or
        clear starts it again and is a full one."""
        try:
            call(*args)
        except BaseException:
            self._started = self._shown = None
            raise

    def _call(self, name: str, *args) -> None:
        result = getattr(self._epd, name)(*args)
        if result not in (None, 0):
            raise DisplayError(f"{self.model}.{name}() failed (returned {result!r})")
