"""The wires between the Raspberry Pi and the IT8951 controller.

The driver talks to the controller through a :class:`Bus`: SPI transfers plus two GPIO
lines, reset (GPIO 17) and busy (GPIO 24, called HRDY in the datasheet: high means the
controller is ready for the next transfer). Chip select stays with the kernel's SPI
driver, so no other pins are claimed and a HiFiBerry DAC+ keeps its pins.

:class:`SpiBus` is the real one, using ``spidev`` and ``gpiod``. Tests use a fake bus, so
they run without hardware. ``spidev`` and ``gpiod`` are imported only when a
:class:`SpiBus` is made.
"""

from __future__ import annotations

from typing import Protocol

RESET_PIN = 17
BUSY_PIN = 24


class Bus(Protocol):
    """What the driver needs from the wires."""

    #: The most bytes one SPI transfer may carry.
    block: int

    def transfer(self, data: bytes, hz: int) -> bytes:
        """Send ``data`` in one chip-select window and return the bytes read back."""

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
        try:
            self._spi = spidev.SpiDev()
            self._spi.open(*spi)
            self._spi.mode = 0
        except BaseException:
            self.close()
            raise
        self.block = _spidev_block_size()

    def transfer(self, data: bytes, hz: int) -> bytes:
        self._spi.max_speed_hz = hz
        return bytes(self._spi.xfer3(data))

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
            return min(int(f.read()), 65536)
    except (OSError, ValueError):
        return 4096
