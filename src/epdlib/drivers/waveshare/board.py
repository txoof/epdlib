"""The wires between the Raspberry Pi and a Waveshare e-Paper HAT.

Waveshare's code talks to the screen through a :class:`Board`: SPI writes plus a few GPIO
lines (pins of the Pi's 40-pin header, by GPIO number, not by pin position). Chip select
(the pin that tells the screen "this transfer is for you") stays with the kernel's SPI
driver, so it is not claimed here.

:class:`GpioBoard` is the real one, using ``spidev`` and ``gpiod``. Tests use a fake board,
so they run without hardware. ``spidev`` and ``gpiod`` are imported only when a
:class:`GpioBoard` is made.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from .. import DisplayError

# The pins of Waveshare's HATs, by GPIO number. They are kept only here, so a setting for
# other pins can be added later in one place.
RST_PIN = 17  # reset, output
DC_PIN = 25  # data (high) or command (low), output
CS_PIN = 8  # chip select: used by the kernel's SPI driver, never claimed here
BUSY_PIN = 24  # busy, input
PWR_PIN = 18  # power for the screen on newer HATs, output


class Board(Protocol):
    """What Waveshare's code needs from the wires."""

    def write_pin(self, pin: int, value: bool) -> None:
        """Set an output pin high (``True``) or low."""

    def read_pin(self, pin: int) -> bool:
        """True when the input pin is high."""

    def spi_write(self, data: bytes) -> None:
        """Send ``data`` over SPI, reading nothing back."""

    def close(self) -> None:
        """Release SPI and the GPIO lines. Safe to call more than once."""


class GpioBoard:
    """The real board: ``spidev`` for SPI and ``gpiod`` (version 2) for the pins.

    ``outputs`` start low. ``busy`` is read with the pin's pull-down resistor on, as
    Waveshare's code does.
    """

    def __init__(
        self,
        outputs: Iterable[int],
        busy: int,
        *,
        spi: tuple[int, int] = (0, 0),
        hz: int = 4_000_000,
        chip: str = "/dev/gpiochip0",
    ):
        import gpiod
        import spidev
        from gpiod.line import Bias, Direction, Value

        self._active = Value.ACTIVE
        self._inactive = Value.INACTIVE
        self._spi = None
        self._lines = None
        self._names = {pin: f"GPIO{pin}" for pin in (*outputs, busy)}
        try:
            with gpiod.Chip(chip) as c:
                for name in self._names.values():
                    c.line_offset_from_id(name)  # raises if the chip has no such pin
        except (OSError, ValueError) as err:
            raise DisplayError(
                f"{chip} is not the Raspberry Pi's 40-pin header: pass the right chip"
            ) from err
        config = {
            self._names[pin]: gpiod.LineSettings(
                direction=Direction.OUTPUT, output_value=Value.INACTIVE
            )
            for pin in outputs
        }
        config[self._names[busy]] = gpiod.LineSettings(
            direction=Direction.INPUT, bias=Bias.PULL_DOWN
        )
        try:
            self._lines = gpiod.request_lines(chip, consumer="epdlib-waveshare", config=config)
        except OSError as err:
            pins = ", ".join(self._names.values())
            raise DisplayError(
                f"cannot claim {pins}: another program is using them ({err})"
            ) from err
        try:
            self._spi = spidev.SpiDev()
            self._spi.open(*spi)
            self._spi.mode = 0
            self._spi.max_speed_hz = hz
        except FileNotFoundError as err:
            self.close()
            raise DisplayError(
                f"/dev/spidev{spi[0]}.{spi[1]} is missing: turn on SPI (sudo raspi-config, "
                "Interface Options, SPI) and restart"
            ) from err
        except BaseException:
            self.close()
            raise

    def write_pin(self, pin: int, value: bool) -> None:
        self._lines.set_value(self._names[pin], self._active if value else self._inactive)

    def read_pin(self, pin: int) -> bool:
        return self._lines.get_value(self._names[pin]) == self._active

    def spi_write(self, data: bytes) -> None:
        self._spi.writebytes2(data)

    def close(self) -> None:
        spi, self._spi = self._spi, None
        lines, self._lines = self._lines, None
        try:
            if spi is not None:
                spi.close()
        finally:
            if lines is not None:
                lines.release()
