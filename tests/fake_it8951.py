"""A pretend IT8951 controller behind a pretend bus, so the driver is tested without hardware.

It understands the commands the driver sends, keeps the loaded pixels in an image, and
records every area the driver asks it to draw. Faults are switched on with attributes.
"""

from __future__ import annotations

from PIL import Image

# How many argument words each command takes (VCOM is handled on its own).
_ARGS = {0x0001: 0, 0x0003: 0, 0x0010: 1, 0x0011: 2, 0x0021: 5, 0x0022: 0, 0x0034: 5}
_LUTAFSR = 0x1224
_IMG_ADDR = 0x0012_3456
# 4-bit value of each half of a byte, back to an 8-bit gray value.
_HIGH = bytes((b >> 4) * 17 for b in range(256))
_LOW = bytes((b & 0xF) * 17 for b in range(256))


class FakeIT8951:
    """Pass the instance itself as the driver's ``bus`` (it is called to "open" the bus)."""

    def __init__(self, width=1200, height=825, block=4096):
        self.width, self.height, self.block = width, height, block
        self.memory = Image.new("L", (width, height), 255)
        #: Every draw: (x, y, w, h, mode).
        self.draws: list[tuple[int, int, int, int, int]] = []
        self.commands: list[int] = []
        self.registers: dict[int, int] = {}
        self.vcom = None
        self.opened = 0
        self.closed = 0
        self.in_reset = False
        # Faults
        self.busy_stuck = False  # busy line stays low
        self.redraw_stuck = False  # LUTAFSR never goes back to 0
        self.silent = False  # device info is all zeros
        self._pending: tuple[int, list[int], int] | None = None
        self._reply: list[int] = []
        self._load: tuple[int, int, int, int] | None = None
        self._pixels = bytearray()

    # ---------------------------------------------------------------- bus interface

    def __call__(self):
        self.opened += 1
        return self

    def ready(self) -> bool:
        return not self.busy_stuck and not self.in_reset

    def set_reset(self, active: bool) -> None:
        self.in_reset = active

    def close(self) -> None:
        self.closed += 1

    def transfer(self, data: bytes, hz: int) -> bytes:
        assert len(data) <= self.block, "transfer larger than the spidev limit"
        preamble = int.from_bytes(data[:2], "big")
        body = data[2:]
        if preamble == 0x6000:
            self._start(int.from_bytes(body, "big"))
        elif preamble == 0x0000:
            if self._load is not None and self._pending is None:
                self._pixels += body
            else:
                self._argument(int.from_bytes(body, "big"))
        elif preamble == 0x1000:
            count = (len(data) - 4) // 2
            words, self._reply = self._reply[:count], self._reply[count:]
            words += [0] * (count - len(words))
            return bytes(4) + b"".join(w.to_bytes(2, "big") for w in words)
        else:
            raise AssertionError(f"unknown preamble {preamble:#06x}")
        return bytes(len(data))

    # ---------------------------------------------------------------- the controller

    def _start(self, cmd: int) -> None:
        assert self._pending is None, f"command {cmd:#06x} before the last one got its arguments"
        self.commands.append(cmd)
        if cmd == 0x0302:  # device info
            self._reply = self._device_info()
        elif cmd == 0x0022:  # end of image load
            self._finish_load()
        elif cmd == 0x0039:
            self._pending = (cmd, [], 1)
        elif _ARGS.get(cmd):
            self._pending = (cmd, [], _ARGS[cmd])
        elif cmd not in _ARGS:
            raise AssertionError(f"unknown command {cmd:#06x}")

    def _argument(self, word: int) -> None:
        assert self._pending is not None, "data word without a command"
        cmd, args, need = self._pending
        args.append(word)
        if cmd == 0x0039 and len(args) == 1 and word == 1:
            need = 2  # set VCOM: one more word follows
        if len(args) < need:
            self._pending = (cmd, args, need)
            return
        self._pending = None
        if cmd == 0x0010:
            reg = args[0]
            value = 1 if reg == _LUTAFSR and self.redraw_stuck else self.registers.get(reg, 0)
            self._reply = [value]
        elif cmd == 0x0011:
            self.registers[args[0]] = args[1]
        elif cmd == 0x0021:
            assert args[0] == (1 << 8) | (2 << 4), "expected big-endian 4 bits per pixel"
            self._load = tuple(args[1:])
            self._pixels = bytearray()
        elif cmd == 0x0034:
            self.draws.append(tuple(args))
        elif cmd == 0x0039:
            if args[0] == 1:
                self.vcom = -args[1] / 1000
            else:
                self._reply = [round(-(self.vcom or 0) * 1000)]

    def _finish_load(self) -> None:
        x, y, w, h = self._load
        assert x % 4 == 0 and w % 4 == 0, "area not on a 4-pixel boundary"
        assert len(self._pixels) == w * h // 2, "wrong number of pixel bytes"
        values = bytearray(2 * len(self._pixels))
        values[0::2] = self._pixels.translate(_HIGH)
        values[1::2] = self._pixels.translate(_LOW)
        self.memory.paste(Image.frombytes("L", (w, h), bytes(values)), (x, y))
        self._load = None

    def _device_info(self) -> list[int]:
        if self.silent:
            return [0] * 20

        def text(s: str) -> list[int]:
            raw = s.encode().ljust(16, b"\x00")
            return [int.from_bytes(raw[i : i + 2], "big") for i in range(0, 16, 2)]

        addr = [_IMG_ADDR & 0xFFFF, _IMG_ADDR >> 16]
        return [self.width, self.height, *addr, *text("WS_v.0.2T1"), *text("8M14T")]
