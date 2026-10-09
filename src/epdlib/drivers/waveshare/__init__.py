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

from PIL import Image

from ...modes import ScreenMode
from .. import DisplayError, DisplayInfo, Driver
from .board import BUSY_PIN, DC_PIN, PWR_PIN, RST_PIN, Board, GpioBoard
from .vendor import epdconfig

__all__ = ["MODELS", "WaveshareDriver"]


@dataclass(frozen=True)
class _Calls:
    """Names of the model file's functions for each operation."""

    init: str = "init"
    buffer: str = "getbuffer"
    display: str = "display"
    clear: str = "Clear"


def _model(name: str, width: int, height: int, mode: ScreenMode, tested: bool = False):
    return DisplayInfo(
        model=f"Waveshare {name}", width=width, height=height, mode=mode, tested=tested
    )


#: Supported screens, by the name of Waveshare's file for them (without ``.py``).
MODELS: dict[str, DisplayInfo] = {
    "epd7in5_V2": _model('7.5" V2', 800, 480, ScreenMode.bw()),
}

_CALLS: dict[str, _Calls] = {
    "epd7in5_V2": _Calls(),
}


class WaveshareDriver(Driver):
    """One Waveshare screen.

    - ``model``: a key of :data:`MODELS`, the name of Waveshare's file for the screen,
      e.g. ``"epd7in5_V2"``.
    - ``power_pin``: GPIO 18, which switches the screen's power on newer Waveshare HATs
      (default), or ``None`` to leave GPIO 18 alone, for example for a HiFiBerry sound
      card, which also needs it. Other pins are not supported yet.
    - ``timeout``: the longest one operation (init, write, clear, sleep) may take, in
      seconds.

    Only one Waveshare screen can be open at a time in one program.
    """

    def __init__(
        self,
        model: str = "epd7in5_V2",
        *,
        power_pin: int | None = PWR_PIN,
        timeout: float = 30.0,
        board: Callable[..., Board] = GpioBoard,
    ):
        super().__init__(timeout=timeout)
        if model not in MODELS:
            raise ValueError(f"unknown Waveshare model {model!r}; known: {', '.join(MODELS)}")
        if power_pin not in (PWR_PIN, None):
            raise ValueError(f"power_pin must be {PWR_PIN} or None, got {power_pin!r}")
        self.info = MODELS[model]
        self.model = model
        self.power_pin = power_pin
        self._calls = _CALLS[model]
        self._make_board = board
        self._board: Board | None = None
        self._epd = None
        #: The screen was put to sleep (and its power switched off) and not woken since.
        self._asleep = False

    # ------------------------------------------------------------------ interface

    def init(self) -> None:
        self.close()
        epdconfig.start(self.timeout)
        try:
            outputs = (RST_PIN, DC_PIN) + ((PWR_PIN,) if self.power_pin is not None else ())
            self._board = self._make_board(outputs, BUSY_PIN)
            epdconfig.attach(self, self._board, power_pin=self.power_pin is not None)
            self._epd = self._module().EPD()
            self._call(self._calls.init)
        except BaseException:
            self.close()
            raise

    def write(self, image: Image.Image, *, fast: bool = False) -> None:
        image = self.check_image(image)
        self._wake()
        buffer = getattr(self._epd, self._calls.buffer)(image)
        self._call(self._calls.display, buffer)

    def clear(self) -> None:
        self._wake()
        self._call(self._calls.clear)

    def sleep(self) -> None:
        """Put the screen into deep sleep and switch its power off; the next write or clear
        wakes it. Calling it again while the screen sleeps does nothing."""
        if self._epd is not None and not self._asleep:
            epdconfig.start(self.timeout)
            self._epd.sleep()
            self._asleep = True

    def close(self) -> None:
        board, self._board = self._board, None
        self._epd = None
        self._asleep = False
        epdconfig.detach(self)
        if board is not None:
            board.close()

    # ------------------------------------------------------------------ helpers

    def _module(self) -> ModuleType:
        return importlib.import_module(f"{__name__}.vendor.{self.model}")

    def _wake(self) -> None:
        """Start the operation's time limit, and wake a sleeping screen. Waking runs the
        model's init again: after deep sleep the screen needs a reset."""
        if self._epd is None:
            raise DisplayError("screen is closed: call init() first")
        epdconfig.start(self.timeout)
        if self._asleep:
            self._call(self._calls.init)
            self._asleep = False

    def _call(self, name: str, *args) -> None:
        result = getattr(self._epd, name)(*args)
        if result not in (None, 0):
            raise DisplayError(f"{self.model}.{name}() failed (returned {result!r})")
