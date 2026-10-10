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
from collections.abc import Callable
from dataclasses import dataclass
from types import ModuleType

from PIL import Image, ImageChops

from ...modes import ScreenMode
from .. import DisplayError, DisplayInfo, Driver
from .board import BUSY_PIN, DC_PIN, PWR_PIN, RST_PIN, Board, GpioBoard
from .vendor import epdconfig

__all__ = ["MODELS", "WaveshareDriver"]


@dataclass(frozen=True)
class _Calls:
    """Names of the model file's functions for each operation.

    ``fast_init`` and ``fast`` are for fast writes: the model's init for its fast mode,
    and a function ``(epd, buffer)`` that shows a buffer in that mode. ``None``: the model
    has no fast mode, and every write is full.
    """

    init: str = "init"
    buffer: str = "getbuffer"
    display: str = "display"
    clear: str = "Clear"
    fast_init: str | None = None
    fast: Callable | None = None


def _display(epd, buffer) -> None:
    epd.display(buffer)


# The 7.5" V2's fast write is Waveshare's fast full refresh (init_fast). Its partial
# refresh (init_part + display_Partial) was tried too: on the screen it also flashed the
# whole screen and took as long (3.7 s), but depends on the controller remembering the
# last image, so the full refresh was chosen (txoof, 2026-10-10).
_CALLS: dict[str, _Calls] = {
    "epd7in5_V2": _Calls(fast_init="init_fast", fast=_display),
}


def _model(file: str, name: str, width: int, height: int, mode: ScreenMode, tested=False):
    return DisplayInfo(
        model=f"Waveshare {name}",
        width=width,
        height=height,
        mode=mode,
        fast_refresh=_CALLS[file].fast is not None,
        tested=tested,
    )


#: Supported screens, by the name of Waveshare's file for them (without ``.py``).
MODELS: dict[str, DisplayInfo] = {
    "epd7in5_V2": _model("epd7in5_V2", '7.5" V2', 800, 480, ScreenMode.bw(), tested=True),
}


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
        timeout: float = 30.0,
        board: Callable[..., Board] = GpioBoard,
    ):
        super().__init__(timeout=timeout)
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
        self._begin()
        calls = self._calls
        if fast and calls.fast is not None and self._shown is not None:
            if ImageChops.difference(self._shown, image).getbbox() is None:
                return  # same pixels as on the screen: nothing is sent
            fast = not (self.max_refresh and self._fast_in_row >= self.max_refresh)
        else:
            fast = False
        self._start(calls.fast_init if fast else calls.init)
        buffer = getattr(self._epd, calls.buffer)(image)
        self._shown = None  # unknown until the write has finished
        if fast:
            self._guard(calls.fast, self._epd, buffer)
        else:
            self._guard(self._call, calls.display, buffer)
        self._shown = image.copy()
        self._fast_in_row = self._fast_in_row + 1 if fast else 0

    def clear(self) -> None:
        self._begin()
        self._start(self._calls.init)
        self._shown = None
        self._guard(self._call, self._calls.clear)
        self._shown = Image.new(self.info.mode.pil_mode, (self.info.width, self.info.height), 255)
        self._fast_in_row = 0

    def sleep(self) -> None:
        """Put the screen into deep sleep and switch its power off; the next write or clear
        wakes it. Calling it again while the screen sleeps does nothing."""
        if self._epd is not None and not self._asleep:
            epdconfig.start(self.timeout)
            # Set first: if sleep fails part way, the screen may be off already.
            self._asleep, self._started = True, None
            self._epd.sleep()

    def close(self) -> None:
        board, self._board = self._board, None
        self._epd = None
        self._asleep, self._started, self._shown = False, None, None
        epdconfig.detach(self)
        if board is not None:
            board.close()

    # ------------------------------------------------------------------ helpers

    def _module(self) -> ModuleType:
        return importlib.import_module(f"{__name__}.vendor.{self.model}")

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
            self._guard(self._call, init)
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
