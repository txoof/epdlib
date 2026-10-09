"""A pretend Waveshare HAT, so the driver and Waveshare's model files are tested without
hardware.

It records every pin change and every SPI write (as a command or as data, by the level of
the data/command pin), and answers the busy pin. Faults are switched on with attributes.
"""

from __future__ import annotations

from epdlib.drivers.waveshare.board import DC_PIN, PWR_PIN, RST_PIN


class FakeBoard:
    """Pass the instance itself as the driver's ``board`` (it is called to "open" it).

    ``idle`` is the level of the busy pin when the screen is ready: 1 for the 7.5" V2.
    """

    def __init__(self, idle: int = 1):
        self.idle = idle
        self.pins: dict[int, bool] = {}
        self.outputs: tuple[int, ...] = ()
        self.busy: int | None = None
        #: Every SPI write: ("cmd", bytes) or ("data", bytes).
        self.sent: list[tuple[str, bytes]] = []
        self.opened = 0
        self.closed = 0
        self.resets = 0
        self.busy_reads = 0
        self.busy_stuck = False  # the busy pin never says "ready"
        #: Reads that answer "busy" before the pin says "ready" (then counts down to 0).
        self.busy_for = 0

    def __call__(self, outputs, busy):
        self.opened += 1
        self.outputs, self.busy = tuple(outputs), busy
        self.pins = {pin: False for pin in self.outputs}
        return self

    def write_pin(self, pin: int, value: bool) -> None:
        assert pin in self.outputs, f"GPIO {pin} was not claimed"
        if pin == RST_PIN and self.pins[pin] and not value:
            self.resets += 1  # reset is held low after being high
        self.pins[pin] = value

    def read_pin(self, pin: int) -> bool:
        assert pin == self.busy, f"GPIO {pin} is not the busy pin"
        self.busy_reads += 1
        if self.busy_for:
            self.busy_for -= 1
            return bool(1 - self.idle)
        return bool(1 - self.idle if self.busy_stuck else self.idle)

    def spi_write(self, data: bytes) -> None:
        assert isinstance(data, bytes)
        assert self.pins.get(PWR_PIN, True), "SPI write while the screen's power is off"
        assert self.pins[RST_PIN], "SPI write while the reset pin holds the screen in reset"
        self.sent.append(("data" if self.pins[DC_PIN] else "cmd", data))

    def close(self) -> None:
        self.closed += 1

    # ---------------------------------------------------------------- for the tests

    @property
    def commands(self) -> list[int]:
        return [data[0] for kind, data in self.sent if kind == "cmd"]

    def data_after(self, command: int) -> bytes:
        """The data sent after the last time ``command`` was sent."""
        start = max(i for i, (k, d) in enumerate(self.sent) if k == "cmd" and d[0] == command)
        out = bytearray()
        for kind, data in self.sent[start + 1 :]:
            if kind == "cmd":
                break
            out += data
        return bytes(out)
