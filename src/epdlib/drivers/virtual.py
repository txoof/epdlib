"""A driver that writes PNG files instead of using a screen.

Used for tests, the docs gallery and previews. It can pretend to be any screen: any size
and any :class:`~epdlib.modes.ScreenMode`.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from ..modes import ScreenMode
from . import DisplayError, DisplayInfo, Driver


class VirtualDriver(Driver):
    """Saves every image it is sent as a PNG file in ``folder``.

    Files are numbered (``0001.png``, ``0002.png``, ...) and the newest is also saved as
    ``latest.png``. ``keep`` is how many numbered files are kept; older ones are deleted.
    The newest image is also available as :attr:`image`.
    """

    def __init__(
        self,
        width: int,
        height: int,
        mode: ScreenMode,
        folder: str | Path,
        *,
        fast_refresh: bool = True,
        keep: int = 50,
        timeout: float = 60.0,
    ):
        super().__init__(timeout=timeout)
        if keep < 1:
            raise ValueError("keep must be at least 1")
        self.info = DisplayInfo(
            model=f"virtual {width}x{height} {mode.kind}",
            width=width,
            height=height,
            mode=mode,
            fast_refresh=fast_refresh,
            tested=True,
        )
        self.folder = Path(folder)
        self.keep = keep
        self.count = 0
        self.image: Image.Image | None = None
        self.awake = False
        self.asleep = False
        #: Every operation, in order, for tests: ("write", "full"), ("sleep",), ...
        self.log: list[tuple[str, ...]] = []

    def init(self) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        self.awake = True
        self.asleep = False
        self.log.append(("init",))

    def write(self, image: Image.Image, *, fast: bool = False) -> None:
        self._check_awake()
        image = self.check_image(image)
        refresh = "fast" if fast and self.info.fast_refresh else "full"
        self._save(image)
        self.log.append(("write", refresh))

    def clear(self) -> None:
        self._check_awake()
        size = (self.info.width, self.info.height)
        self._save(self.info.mode.finish(Image.new("L", size, 255)))
        self.log.append(("clear",))

    def sleep(self) -> None:
        if self.awake:
            self.awake, self.asleep = False, True
        self.log.append(("sleep",))

    def close(self) -> None:
        self.awake = self.asleep = False
        self.log.append(("close",))

    def _check_awake(self) -> None:
        if self.asleep:
            self.awake, self.asleep = True, False
            self.log.append(("wake",))
        elif not self.awake:
            raise DisplayError("screen is closed: call init() first")

    def _save(self, image: Image.Image) -> None:
        self.count += 1
        self.image = image.copy()
        image.save(self.folder / f"{self.count:04d}.png")
        image.save(self.folder / "latest.png")
        old = self.folder / f"{self.count - self.keep:04d}.png"
        if self.count > self.keep:
            old.unlink(missing_ok=True)
