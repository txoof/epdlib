"""What a screen can show, and how drawn images are reduced to that.

Every block is drawn in a working image ("L" for gray, "RGB" for colour) and then reduced
to the screen's mode. Text is reduced without dithering (each pixel goes to the nearest
colour the screen has), so it stays sharp. Images and shapes are dithered: dot patterns
fake the in-between shades.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from PIL import Image, ImageChops, ImageColor

Kind = Literal["bw", "gray", "palette", "rgb"]

#: The colours of the common 7-colour Waveshare screens (ACeP).
SEVEN_COLORS: tuple[str, ...] = (
    "black",
    "white",
    "green",
    "blue",
    "red",
    "yellow",
    "orange",
)


@dataclass(frozen=True)
class ScreenMode:
    """What a screen can show.

    Make one with :meth:`bw`, :meth:`gray`, :meth:`palette` or :meth:`rgb`.
    """

    kind: Kind
    levels: int = 2
    colors: tuple[str, ...] = ()
    #: What each of :attr:`colors` really looks like on the panel, as ``(r, g, b)``, or
    #: empty when not measured. Dots are chosen by these; :attr:`colors` are sent.
    measured: tuple[tuple[int, int, int], ...] = ()

    @classmethod
    def bw(cls) -> ScreenMode:
        """Black and white only (1 bit per pixel)."""
        return cls("bw", levels=2)

    @classmethod
    def gray(cls, levels: int) -> ScreenMode:
        """``levels`` evenly spaced shades of gray from black to white (e.g. 4 or 16)."""
        if not 2 <= levels <= 256:
            raise ValueError(f"gray levels must be between 2 and 256, got {levels}")
        return cls("gray", levels=levels)

    @classmethod
    def palette(
        cls,
        colors: tuple[str, ...] = SEVEN_COLORS,
        measured: tuple[tuple[int, int, int], ...] = (),
    ) -> ScreenMode:
        """A fixed set of colours, given as names or ``#rrggbb``. Must include black and white.

        ``colors`` are the values the screen is sent. Colour panels often look much
        darker than these values; ``measured`` (optional) gives what each colour really
        looks like, in the same order, so dots are chosen by the panel's real colours.
        """
        rgb = {ImageColor.getrgb(c) for c in colors}
        if (0, 0, 0) not in rgb or (255, 255, 255) not in rgb:
            raise ValueError("a palette must include black and white")
        measured = tuple(tuple(c) for c in measured)
        if measured and len(measured) != len(colors):
            raise ValueError(
                f"measured needs one colour per palette colour: {len(colors)}, got {len(measured)}"
            )
        for c in measured:
            if len(c) != 3 or not all(isinstance(v, int) and 0 <= v <= 255 for v in c):
                raise ValueError(f"a measured colour must be (r, g, b) with 0-255 each, got {c}")
        return cls("palette", levels=len(colors), colors=tuple(colors), measured=measured)

    @classmethod
    def rgb(cls) -> ScreenMode:
        """Full colour."""
        return cls("rgb", levels=256)

    @property
    def has_color(self) -> bool:
        return self.kind in ("palette", "rgb")

    @property
    def pil_mode(self) -> str:
        """The Pillow mode of finished images: ``1``, ``L`` or ``RGB``.

        Palette screens get ``RGB`` images that use only the palette's colours.
        """
        return {"bw": "1", "gray": "L", "palette": "RGB", "rgb": "RGB"}[self.kind]

    def work_mode(self, color: bool) -> str:
        """The Pillow mode a block is drawn in before it is reduced."""
        return "RGB" if color and self.has_color else "L"

    def ink(self, value: str, color: bool) -> int | tuple[int, int, int]:
        """Turn a colour name or ``#rrggbb`` into a pixel value for :meth:`work_mode`."""
        return ImageColor.getcolor(value, self.work_mode(color))

    def reduce(self, image: Image.Image, *, dither: bool, color: bool) -> Image.Image:
        """Reduce a drawn block to what the screen can show.

        Returns an ``L`` image (gray and black-and-white screens) or an ``RGB`` image
        (colour screens). ``color=False`` draws a block in gray or black and white even
        on a colour screen.
        """
        if color and self.kind == "rgb":
            return image.convert("RGB")
        if color and self.kind == "palette":
            image = image.convert("RGB")
            if not self.measured:
                return _quantize(image, self.colors, dither).convert("RGB")
            reduced = _quantize(_exact_to_measured(image, self), self.measured, dither)
            reduced.putpalette(_palette_data(self.colors))  # send the screen's own values
            return reduced.convert("RGB")
        gray = image.convert("L")
        levels = self.levels if self.kind == "gray" else 2
        if self.kind in ("palette", "rgb") and not color:
            # Colour screens have no shades of gray in their palette: black and white only.
            levels = 2 if self.kind == "palette" else 256
        if levels >= 256:
            reduced = gray
        elif dither:
            steps = [round(i * 255 / (levels - 1)) for i in range(levels)]
            reduced = _quantize(gray.convert("RGB"), [(s, s, s) for s in steps], True).convert("L")
        else:
            reduced = gray.point(_nearest_level_table(levels))
        return reduced.convert("RGB") if self.has_color else reduced

    def finish(self, image: Image.Image) -> Image.Image:
        """Convert a finished screen image to :attr:`pil_mode`."""
        return image.convert(self.pil_mode) if image.mode != self.pil_mode else image

    def convert(self, image: Image.Image) -> Image.Image:
        """Convert any image (for example one a program drew itself) to this mode, dithered."""
        if has_transparency(image):
            image = flatten(image)
        return self.finish(self.reduce(image, dither=True, color=True))


def _nearest_level_table(levels: int) -> list[int]:
    step = 255 / (levels - 1)
    return [round(round(v / step) * step) for v in range(256)]


def _palette_data(colors) -> list[int]:
    rgb = [c if isinstance(c, tuple) else ImageColor.getrgb(c) for c in colors]
    # Pad by repeating the first colour, so no unused black entries are matched.
    return [v for c in rgb + [rgb[0]] * (256 - len(rgb)) for v in c]


def _exact_to_measured(image: Image.Image, mode: ScreenMode) -> Image.Image:
    """Swap pixels that are exactly one of the screen's colours for its measured colour,
    so areas drawn in a screen colour stay solid instead of getting dots of other colours."""
    nearest = _quantize(image, mode.colors, False)
    r, g, b = ImageChops.difference(image, nearest.convert("RGB")).split()
    exact = ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: 255 if v == 0 else 0)
    nearest.putpalette(_palette_data(mode.measured))
    return Image.composite(nearest.convert("RGB"), image, exact.convert("1"))


def _quantize(image: Image.Image, colors, dither: bool) -> Image.Image:
    pal = Image.new("P", (1, 1))
    pal.putpalette(_palette_data(colors))
    method = Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE
    return image.quantize(palette=pal, dither=method)


def has_transparency(image: Image.Image) -> bool:
    """True when the image has see-through parts (an alpha channel or a transparent colour)."""
    return image.mode in ("RGBA", "LA", "PA", "RGBa", "La") or "transparency" in image.info


def flatten(image: Image.Image, background: str = "white") -> Image.Image:
    """Put a transparent image on a plain background."""
    rgba = image.convert("RGBA")
    base = Image.new("RGBA", rgba.size, background)
    base.alpha_composite(rgba)
    return base.convert("RGB")
