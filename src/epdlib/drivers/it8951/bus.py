"""The wires between the Raspberry Pi and the IT8951 controller.

The driver talks to the controller through a :class:`Bus`: SPI transfers plus two GPIO
lines (pins of the Pi's 40-pin header, by GPIO number, not by pin position): reset
(GPIO 17) and busy (GPIO 24, called HRDY in the datasheet: high means the controller is
ready for the next transfer). Chip select (the pin that tells the controller "this
transfer is for you") stays with the kernel's SPI driver, so no other pins are claimed
and a HiFiBerry DAC+ (a sound card board that uses GPIO 2, 3 and 18 to 21) keeps its pins.

:class:`SpiBus` is the real one, using ``spidev`` and ``gpiod``. Tests use a fake bus, so
they run without hardware. ``spidev`` and ``gpiod`` are imported only when a
:class:`SpiBus` is made.
"""

from __future__ import annotations

from typing import Protocol

from .. import DisplayError

#: Pin names as the Pi's GPIO chip calls them. Looking pins up by name makes sure they are
#: on the 40-pin header, whichever number the chip has.
RESET_PIN = "GPIO17"
BUSY_PIN = "GPIO24"


class Bus(Protocol):
    """What the driver needs from the wires."""

    #: The most bytes one SPI transfer may carry.
    block: int

    def transfer(self, data: bytes, hz: int) -> bytes:
        """Send ``data`` in one chip-select window and return the bytes read back."""

    def write(self, data: bytes, hz: int) -> None:
        """Send ``data`` in one chip-select window, reading nothing back (for pixels)."""

    def ready(self) -> bool:
        """True when the busy line is high (the controller can take the next transfer)."""

    def set_reset(self, active: bool) -> None:
        """Hold the reset line low (``True``) or let the controller run (``False``)."""

    def close(self) -> None:
        """Release SPI and the GPIO lines. Safe to call more than once."""


class SpiBus:
    """The real bus: ``spidev`` for SPI and ``gpiod`` (version 2) for the two pins."""

    def __init__(self, spi: tuple[int, int] = (0, 0), chip: str = "/dev/gpiochip0"):
        import gpiod
        import spidev
        from gpiod.line import Direction, Value

        self._active = Value.ACTIVE
        self._inactive = Value.INACTIVE
        self._spi = None
        self._lines = None
        self._hz = 0
        try:
            with gpiod.Chip(chip) as c:
                for name in (RESET_PIN, BUSY_PIN):
                    c.line_offset_from_id(name)  # raises if the chip has no such pin
        except (OSError, ValueError) as err:
            raise DisplayError(
                f"{chip} is not the Raspberry Pi's 40-pin header (no {RESET_PIN}/{BUSY_PIN}): "
                "pass the right chip"
            ) from err
        try:
            self._lines = gpiod.request_lines(
                chip,
                consumer="epdlib-it8951",
                config={
                    RESET_PIN: gpiod.LineSettings(
                        direction=Direction.OUTPUT, output_value=Value.ACTIVE
                    ),
                    BUSY_PIN: gpiod.LineSettings(direction=Direction.INPUT),
                },
            )
        except OSError as err:
            raise DisplayError(
                f"cannot claim {RESET_PIN} and {BUSY_PIN}: another program is using them ({err})"
            ) from err
        try:
            self._spi = spidev.SpiDev()
            self._spi.open(*spi)
            self._spi.mode = 0
        except FileNotFoundError as err:
            self.close()
            raise DisplayError(
                f"/dev/spidev{spi[0]}.{spi[1]} is missing: turn on SPI (sudo raspi-config, "
                "Interface Options, SPI) and restart"
            ) from err
        except BaseException:
            self.close()
            raise
        self.block = _spidev_block_size()

    def transfer(self, data: bytes, hz: int) -> bytes:
        return bytes(self._spi.xfer3(data, hz))

    def write(self, data: bytes, hz: int) -> None:
        if hz != self._hz:
            self._spi.max_speed_hz = self._hz = hz
        self._spi.writebytes2(data)

    def ready(self) -> bool:
        return self._lines.get_value(BUSY_PIN) == self._active

    def set_reset(self, active: bool) -> None:
        # The reset line is "active low": low holds the controller in reset.
        self._lines.set_value(RESET_PIN, self._inactive if active else self._active)

    def close(self) -> None:
        spi, self._spi = self._spi, None
        lines, self._lines = self._lines, None
        try:
            if spi is not None:
                spi.close()
        finally:
            if lines is not None:
                lines.release()


def _spidev_block_size() -> int:
    """The kernel's limit for one spidev transfer (4096 bytes unless raised in cmdline.txt)."""
    try:
        with open("/sys/module/spidev/parameters/bufsiz") as f:
            return max(64, min(int(f.read()), 65536))
    except (OSError, ValueError):
        return 4096
