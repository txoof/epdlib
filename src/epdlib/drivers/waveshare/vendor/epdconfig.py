"""epdlib's replacement for Waveshare's ``epdconfig.py``. Written for epdlib, not copied.

Waveshare's file for each screen model (the ``epd*.py`` files next to this one, copied
unchanged) does ``from . import epdconfig`` and calls the functions below for every pin
change, SPI write and wait. Waveshare's own ``epdconfig.py`` uses ``gpiozero`` and waits
for the busy pin forever; this one uses a :class:`~epdlib.drivers.waveshare.board.Board`
(``gpiod`` and ``spidev``) and stops a wait when the operation's time limit has run out.

:class:`~epdlib.drivers.waveshare.WaveshareDriver` connects a board with :func:`attach`
before it calls the model's code, and disconnects it with :func:`detach`. Only one screen
can be connected at a time in one program, because the model files share this module.
"""

from __future__ import annotations

import math
import time

from ... import DisplayError, DisplayTimeout
from ..board import BUSY_PIN, CS_PIN, DC_PIN, PWR_PIN, RST_PIN, Board

__all__ = ["BUSY_PIN", "CS_PIN", "DC_PIN", "PWR_PIN", "RST_PIN"]

_board: Board | None = None
_owner: object | None = None
_use_power = True
_deadline = math.inf
_timeout = 0.0


def attach(owner: object, board: Board, *, power_pin: bool) -> None:
    """Connect ``board``. ``power_pin=False`` leaves the PWR pin alone."""
    global _board, _owner, _use_power
    if _owner is not None and _owner is not owner:
        raise DisplayError("another Waveshare screen is open in this program: close it first")
    _board, _owner, _use_power = board, owner, power_pin


def detach(owner: object) -> None:
    """Disconnect the board, if ``owner`` connected it."""
    global _board, _owner
    if _owner is owner:
        _board, _owner = None, None


def start(timeout: float) -> None:
    """Start the time limit for one operation: waits stop ``timeout`` seconds from now."""
    global _deadline, _timeout
    _deadline = time.monotonic() + timeout
    _timeout = timeout


def _connected() -> Board:
    if _board is None:
        raise DisplayError("screen is closed: call init() first")
    return _board


# ---------------------------------------------------------------- called by the model files


def digital_write(pin: int, value: int) -> None:
    if pin == CS_PIN or (pin == PWR_PIN and not _use_power):
        return  # chip select belongs to the kernel's SPI driver
    _connected().write_pin(pin, bool(value))


def digital_read(pin: int) -> int:
    """Read the busy pin. The model files read it in a loop until the screen is ready, so
    the time limit is checked here, and a short pause keeps the loop from using a whole
    processor core."""
    if pin != BUSY_PIN:
        raise DisplayError(f"reading GPIO {pin} is not supported")
    board = _connected()
    if time.monotonic() > _deadline:
        raise DisplayTimeout(f"screen did not finish within {_timeout} s: the busy pin stayed on")
    time.sleep(0.001)
    return int(board.read_pin(pin))


def delay_ms(delaytime: float) -> None:
    time.sleep(delaytime / 1000.0)


def spi_writebyte(data) -> None:
    _connected().spi_write(_to_bytes(data))


spi_writebyte2 = spi_writebyte


class _Spi:
    """Some model files call ``epdconfig.SPI.writebytes2`` directly."""

    def writebytes(self, data) -> None:
        spi_writebyte(data)

    writebytes2 = writebytes


SPI = _Spi()


def module_init(cleanup: bool = False) -> int:
    """Called at the start of each of the model's ``init`` functions: power on."""
    if cleanup:
        raise DisplayError("this model needs Waveshare's software SPI, which epdlib does not have")
    board = _connected()
    if _use_power:
        board.write_pin(PWR_PIN, True)
    return 0


def module_exit(cleanup: bool = False) -> None:
    """Called at the end of the model's ``sleep``: all outputs low, power off. The pins and
    SPI stay claimed until the driver's ``close()``."""
    board = _connected()
    board.write_pin(RST_PIN, False)
    board.write_pin(DC_PIN, False)
    if _use_power:
        board.write_pin(PWR_PIN, False)


def _to_bytes(data) -> bytes:
    if isinstance(data, bytes | bytearray):
        return bytes(data)
    try:
        return bytes(data)
    except ValueError:
        # Some model files send inverted values such as ~0x00 == -1; spidev keeps the
        # lowest 8 bits of each number, so the same is done here.
        return bytes(v & 0xFF for v in data)
