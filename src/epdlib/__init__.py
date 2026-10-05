"""epdlib: draw layouts and show them on e-paper and other frame-buffered displays."""

from importlib.metadata import version

from .geometry import Box
from .layout import Layout, PreparedLayout
from .modes import SEVEN_COLORS, ScreenMode
from .spec import LayoutError

__version__ = version("epdlib")

__all__ = ["SEVEN_COLORS", "Box", "Layout", "LayoutError", "PreparedLayout", "ScreenMode"]
