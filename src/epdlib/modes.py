"""What a screen can show, and how drawn images are reduced to that.

Every block is drawn in a working image ("L" for gray, "RGB" for colour) and then reduced
to the screen's mode. Text is reduced without dithering (each pixel goes to the nearest
colour the screen has), so it stays sharp. Images and shapes are dithered: dot patterns
fake the in-between shades. There are three ways to place the dots (see :data:`DITHERS`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from PIL import Image, ImageChops, ImageColor

Kind = Literal["bw", "gray", "palette", "rgb"]

#: Ways to dither. ``photo``: Floyd-Steinberg, each pixel's rounding error (the difference
#: between the wanted shade and the shade the pixel got) is passed to its neighbours; best
#: for photos, but on large flat gray areas a row of dots can slip.
#: ``pattern``: a fixed 8x8 Bayer pattern; flat areas stay even and never slip, best for
#: drawn graphics. ``smooth``: Atkinson, the most even gray overall, but slow (plain
#: Python: about 3.4 s for a whole 800x480 image on a Pi 3). Colour blocks on colour
#: (palette) screens use the ``photo`` method for all three, for now.
DITHERS = ("photo", "pattern", "smooth")

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
        measured: tuple[str | tuple[int, int, int], ...] = (),
    ) -> ScreenMode:
        """A fixed set of colours, given as names or ``#rrggbb``. Must include black and white.

        ``colors`` are the values the screen is sent. Colour panels often look much
        darker than these values; ``measured`` (optional) gives what each colour really
        looks like, in the same order, as ``(r, g, b)`` or ``#rrggbb``. Dots are then
        chosen by the panel's real colours; text and areas drawn in one of ``colors``
        are not changed.
        """
        rgb = {ImageColor.getrgb(c) for c in colors}
        if (0, 0, 0) not in rgb or (255, 255, 255) not in rgb:
            raise ValueError("a palette must include black and white")
        measured = tuple(_measured_rgb(c) for c in measured)
        if measured and len(measured) != len(colors):
            raise ValueError(
                f"measured needs one colour per palette colour: {len(colors)}, got {len(measured)}"
            )
        if len(set(measured)) != len(measured):
            raise ValueError("measured colours must all be different")
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

    def reduce(self, image: Image.Image, *, dither: str | None, color: bool) -> Image.Image:
        """Reduce a drawn block to what the screen can show.

        ``dither`` is one of :data:`DITHERS`, or ``None`` for no dithering (each pixel
        goes to the nearest shade, as for text). Returns an ``L`` image (gray and
        black-and-white screens) or an ``RGB`` image (colour screens). ``color=False``
        draws a block in gray or black and white even on a colour screen.
        """
        if dither is not None and dither not in DITHERS:
            raise ValueError(f"dither must be one of {', '.join(DITHERS)} or None, got {dither!r}")
        if color and self.kind == "rgb":
            return image.convert("RGB")
        if color and self.kind == "palette":
            image = image.convert("RGB")
            # Every dither choice uses Floyd-Steinberg here for now (no colour patterns yet).
            if not (self.measured and dither is not None):
                # Without dithering (text), each pixel goes to the nearest screen value as
                # before: matched to measured colours, soft text edges got coloured pixels.
                return _quantize(image, self.colors, dither is not None).convert("RGB")
            reduced = _quantize(_exact_to_measured(image, self), self.measured, True)
            reduced.putpalette(_palette_data(self.colors))  # send the screen's own values
            return reduced.convert("RGB")
        gray = image.convert("L")
        levels = self.levels if self.kind == "gray" else 2
        if self.kind in ("palette", "rgb") and not color:
            # Colour screens have no shades of gray in their palette: black and white only.
            levels = 2 if self.kind == "palette" else 256
        if levels >= 256:
            reduced = gray
        elif dither == "photo":
            steps = [round(i * 255 / (levels - 1)) for i in range(levels)]
            reduced = _quantize(gray.convert("RGB"), [(s, s, s) for s in steps], True).convert("L")
        elif dither == "pattern":
            reduced = _ordered(gray, levels)
        elif dither == "smooth":
            reduced = _atkinson(gray, levels)
        else:
            reduced = gray.point(_nearest_level_table(levels))
        return reduced.convert("RGB") if self.has_color else reduced

    def finish(self, image: Image.Image) -> Image.Image:
        """Convert a finished screen image to :attr:`pil_mode`."""
        return image.convert(self.pil_mode) if image.mode != self.pil_mode else image

    def convert(self, image: Image.Image, dither: str = "photo") -> Image.Image:
        """Convert any image (for example one a program drew itself) to this mode.

        ``dither`` is one of :data:`DITHERS`. The default ``"photo"`` suits photos;
        ``"pattern"`` suits drawn graphics with flat gray areas, such as bars and icons;
        ``"smooth"`` is slow (seconds for a whole screen on a Pi 3).
        """
        if has_transparency(image):
            image = flatten(image)
        return self.finish(self.reduce(image, dither=dither, color=True))


def _nearest_level_table(levels: int) -> list[int]:
    step = 255 / (levels - 1)
    return [round(round(v / step) * step) for v in range(256)]


def _bayer(n: int) -> list[list[int]]:
    """The n x n Bayer matrix: the order in which dots are turned on, spread out evenly."""
    m = [[0]]
    while len(m) < n:
        k = len(m)
        m = [
            [4 * m[y % k][x % k] + ((0, 2), (3, 1))[y // k][x // k] for x in range(2 * k)]
            for y in range(2 * k)
        ]
    return m


_BAYER8 = _bayer(8)
# Thresholds 0-254: a pixel moves up one level when its remainder is above its threshold.
_THRESHOLDS = [[(v * 255 + 127) // 64 for v in row] for row in _BAYER8]


def _ordered(gray: Image.Image, levels: int) -> Image.Image:
    """Ordered dithering: each pixel goes to one of its two nearest levels, chosen by its
    place in a fixed 8x8 pattern. It needs no neighbours, so flat areas never slip."""
    w, h = gray.size
    # For each value: the screen level below it, the one above, and how far (0-254) it
    # is from the lower towards the upper one.
    steps = [round(i * 255 / (levels - 1)) for i in range(levels)]
    below = [max(i for i, s in enumerate(steps) if s <= v) for v in range(256)]
    up = [steps[min(i + 1, levels - 1)] for i in below]
    lower = gray.point([steps[i] for i in below])
    upper = gray.point(up)
    rest = gray.point(
        [
            0 if up[v] == steps[i] else round((v - steps[i]) * 255 / (up[v] - steps[i]))
            for v, i in enumerate(below)
        ]
    )
    rows = [bytes(row[x % 8] for x in range(w)) for row in _THRESHOLDS]
    thresholds = Image.frombytes("L", (w, h), b"".join(rows[y % 8] for y in range(h)))
    above = ImageChops.subtract(rest, thresholds).point(lambda v: 255 if v else 0)
    return Image.composite(upper, lower, above.convert("1"))


def _atkinson(gray: Image.Image, levels: int) -> Image.Image:
    """Atkinson dithering: like Floyd-Steinberg, but only 6/8 of each pixel's rounding
    error is passed on, so it cannot build up. Plain Python, so slow."""
    w, h = gray.size
    nearest = _nearest_level_table(levels)
    # Values are kept in 64ths, so small errors are not lost to rounding (on a 16-gray
    # screen most errors are smaller than 8, the share passed to each neighbour).
    px = [v << 6 for v in gray.tobytes()]
    n = w * h
    for i in range(n):
        old = px[i]
        new = nearest[min(max((old + 32) >> 6, 0), 255)]
        px[i] = new
        err = (old - (new << 6)) >> 3
        if err:
            x = i % w
            if x + 1 < w:
                px[i + 1] += err
                if x + 2 < w:
                    px[i + 2] += err
            j = i + w
            if j < n:
                if x:
                    px[j - 1] += err
                px[j] += err
                if x + 1 < w:
                    px[j + 1] += err
                if j + w < n:
                    px[j + w] += err
    return Image.frombytes("L", (w, h), bytes(px))


def _palette_data(colors) -> list[int]:
    rgb = [c if isinstance(c, tuple) else ImageColor.getrgb(c) for c in colors]
    # Pad by repeating the first colour, so no unused black entries are matched.
    return [v for c in rgb + [rgb[0]] * (256 - len(rgb)) for v in c]


def _measured_rgb(colour) -> tuple[int, int, int]:
    if isinstance(colour, str):
        try:
            return ImageColor.getrgb(colour)[:3]
        except ValueError:
            raise ValueError(f"unknown measured colour {colour!r}") from None
    if (
        isinstance(colour, (tuple, list))
        and len(colour) == 3
        and all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 255 for v in colour)
    ):
        return tuple(colour)
    raise ValueError(f"a measured colour must be (r, g, b) with 0-255 each, got {colour!r}")


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
