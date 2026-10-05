"""The interface every display driver follows.

A driver sends finished images to one screen model. See PaperPi
``docs/decisions/display-driver-interface.md`` for the reasons behind these rules:

- Every operation has a time limit. When it runs out, the driver raises
  :class:`DisplayTimeout`. It never waits forever.
- :meth:`Driver.close` always releases the screen's connections, even after an error. Use
  the driver in a ``with`` block to make sure it runs.
- Importing this module never imports hardware libraries. A driver that needs them imports
  them in its own module.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from PIL import Image

from ..modes import ScreenMode

__all__ = ["DisplayError", "DisplayInfo", "DisplayTimeout", "Driver"]


class DisplayError(RuntimeError):
    """The screen did not do what was asked."""


class DisplayTimeout(DisplayError):
    """The screen did not finish within its time limit."""


@dataclass(frozen=True)
class DisplayInfo:
    """Description of one screen model, used for the supported-screens list."""

    model: str
    width: int
    height: int
    mode: ScreenMode
    fast_refresh: bool = False
    tested: bool = False


class Driver(ABC):
    """Base class for display drivers.

    ``timeout`` is the longest any single operation may take, in seconds.
    """

    info: DisplayInfo

    def __init__(self, *, timeout: float = 60.0):
        if timeout <= 0:
            raise ValueError("timeout must be above zero")
        self.timeout = timeout

    @abstractmethod
    def init(self) -> None:
        """Wake the screen and check that it answers."""

    @abstractmethod
    def write(self, image: Image.Image, *, fast: bool = False) -> None:
        """Show ``image``. ``fast`` is a request: screens without a fast refresh do a full one.

        The image must be the screen's size. It is converted to the screen's mode if needed.
        """

    @abstractmethod
    def clear(self) -> None:
        """Make the screen blank (white)."""

    @abstractmethod
    def sleep(self) -> None:
        """Put the screen into low power."""

    @abstractmethod
    def close(self) -> None:
        """Release the screen's connections. Safe to call more than once."""

    def check_image(self, image: Image.Image) -> Image.Image:
        """Check the size of ``image`` and convert it to the screen's mode."""
        size = (self.info.width, self.info.height)
        if image.size != size:
            raise DisplayError(
                f"image is {image.size[0]}x{image.size[1]}, screen is {size[0]}x{size[1]}"
            )
        return self.info.mode.convert(image) if image.mode != self.info.mode.pil_mode else image

    def __enter__(self) -> Driver:
        self.init()
        return self

    def __exit__(self, *exc) -> None:
        self.close()
