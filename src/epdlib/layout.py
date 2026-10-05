"""Layouts: check a layout once, prepare it for a screen, then draw it with new data.

Example::

    layout = Layout({"column": [
        {"name": "title", "type": "text", "size": 1},
        {"size": 4, "row": [
            {"name": "body", "type": "text", "size": 3, "max_lines": 4},
            {"name": "art", "type": "image", "size": 2},
        ]},
    ]})
    page = layout.prepare(800, 480, ScreenMode.gray(16))
    image = page.render({"title": "Hello", "body": "Some text", "art": "cat.png"})
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from . import spec, text
from .geometry import Box, align_offset, place
from .modes import ScreenMode, _flatten
from .spec import Block, LayoutError


class Layout:
    """A checked layout. Raises :class:`LayoutError` when the description is not valid."""

    def __init__(self, data: Any, *, asset_dirs: list[str | Path] | None = None):
        dirs = [Path(d) for d in asset_dirs] if asset_dirs is not None else None
        self.root = spec.parse(data, asset_dirs=dirs)
        self.blocks: dict[str, Block] = {b.name: b for b in spec.blocks(self.root)}

    @classmethod
    def from_json(cls, path: str | Path, *, asset_dirs: list[str | Path]) -> Layout:
        """Read a layout from a JSON file. Fonts and images must be inside ``asset_dirs``."""
        layout = cls.__new__(cls)
        layout.root = spec.load_json(path, asset_dirs=asset_dirs)
        layout.blocks = {b.name: b for b in spec.blocks(layout.root)}
        return layout

    def prepare(self, width: int, height: int, mode: ScreenMode) -> PreparedLayout:
        """Work out block positions and font sizes for one screen. Done once, then reused."""
        return PreparedLayout(self, width, height, mode)


class PreparedLayout:
    """A layout fitted to one screen size and mode. Call :meth:`render` for each update."""

    def __init__(self, layout: Layout, width: int, height: int, mode: ScreenMode):
        self.layout = layout
        self.width = width
        self.height = height
        self.mode = mode
        self.short_side = min(width, height)
        self.boxes: dict[str, Box] = place(layout.root, width, height)
        self.font_sizes: dict[str, int] = {}
        for name, block in layout.blocks.items():
            if block.type == "text":
                self.font_sizes[name] = self._font_size(block)

    def _inner(self, block: Block) -> Box:
        """The part of a block that content goes in: inside its border and padding."""
        box = self.boxes[block.name]
        edge = block.padding.to_pixels(self.short_side)
        edge += block.options["border"].to_pixels(self.short_side)
        return Box(0, 0, box.width, box.height).inset(edge)

    def _font_size(self, block: Block) -> int:
        fixed = block.options["font_size"]
        if fixed is not None:
            return max(1, fixed.to_pixels(self.short_side))
        o = block.options
        inner = self._inner(block)
        size = text.size_for_height(o["font"], inner.height // o["max_lines"])
        # The sample (or else the block's fixed text) must also fit the width.
        sample = o["sample"] or o["text"]
        if sample:
            size = text.size_for_sample(o["font"], size, sample, inner.width, o["max_lines"])
        return size

    def render(self, data: dict[str, Any] | None = None, *, seed: int | None = None) -> Image.Image:
        """Draw the layout with ``data`` (block name -> value) and return the screen image.

        Text blocks take a string, image blocks a Pillow image or a file path, shape blocks a
        dictionary that can change ``fill`` and ``background``. Blocks without a value use
        the value from the layout (``text``, ``image``), or stay empty.
        ``seed`` makes ``random`` alignment repeatable.
        """
        data = dict(data or {})
        unknown = set(data) - set(self.layout.blocks)
        if unknown:
            raise LayoutError(f"no block named {', '.join(sorted(map(repr, unknown)))} in layout")
        rng = random.Random(seed)
        work = "RGB" if self.mode.has_color else "L"
        page = Image.new(work, (self.width, self.height), "white")
        for name, block in self.layout.blocks.items():
            box = self.boxes[name]
            if box.width <= 0 or box.height <= 0:
                continue
            image = self._draw_block(block, box, data.get(name), rng)
            page.paste(image, (box.x, box.y))
        return self.mode.finish(page)

    def _draw_block(self, block: Block, box: Box, value: Any, rng: random.Random) -> Image.Image:
        o = block.options
        color = o["rgb_support"]
        fill, background = (
            (o["background"], o["fill"]) if o["inverse"] else (o["fill"], o["background"])
        )
        if block.type == "shape":
            fill, background = self._shape_colors(value, fill, background)
        canvas = Image.new(self.mode.work_mode(color), box.size, self.mode.ink(background, color))
        draw = ImageDraw.Draw(canvas)
        border = o["border"].to_pixels(self.short_side)
        if border:
            draw.rectangle(
                (0, 0, box.width - 1, box.height - 1),
                outline=self.mode.ink(fill, color),
                width=border,
            )
        inner = self._inner(block)
        if inner.width > 0 and inner.height > 0:
            if block.type == "text":
                self._draw_text(block, draw, inner, value, fill, color, rng)
            elif block.type == "shape":
                self._draw_shape(block, draw, inner, fill, color)
        # Text is never dithered, so it stays sharp. Shapes are, so a gray fill on a
        # black-and-white screen shows as a dot pattern instead of disappearing.
        dither = block.type == "shape"
        result = self.mode.reduce(canvas, dither=dither, color=color)
        if block.type == "image" and inner.width > 0 and inner.height > 0:
            picture = self._image_value(block, value)
            if picture is not None:
                fitted, pos = _fit_image(picture, inner, o, background, rng)
                reduced = self.mode.reduce(fitted, dither=True, color=color)
                result.paste(reduced, pos)
        return result

    def _draw_text(self, block, draw, inner: Box, value, fill, color, rng) -> None:
        o = block.options
        content = o["text"] if value is None else str(value)
        result = text.fit_text(
            o["font"],
            self.font_sizes[block.name],
            content,
            inner.width,
            inner.height,
            o["max_lines"],
            o["shrink"],
            o["ellipsis"],
        )
        offset = (rng.random(), rng.random())
        lines = text.arrange(
            result.font, result.lines, inner.width, inner.height, o["align"], o["valign"], offset
        )
        ink = self.mode.ink(fill, color)
        for line in lines:
            draw.text(
                (inner.x + line.x, inner.y + line.baseline),
                line.text,
                font=result.font,
                fill=ink,
                anchor="ls",
            )

    def _shape_colors(self, value, fill, background):
        if value is None:
            return fill, background
        if not isinstance(value, dict) or set(value) - {"fill", "background"}:
            raise LayoutError("a shape block takes a dictionary with 'fill' and/or 'background'")
        return value.get("fill", fill), value.get("background", background)

    def _draw_shape(self, block, draw, inner: Box, fill, color) -> None:
        o = block.options
        ink = self.mode.ink(fill, color)
        x0, y0 = inner.x, inner.y
        x1, y1 = inner.x + inner.width - 1, inner.y + inner.height - 1
        line = max(1, o["line_width"].to_pixels(self.short_side))
        if o["shape"] == "rectangle":
            draw.rectangle((x0, y0, x1, y1), fill=ink)
        elif o["shape"] == "ellipse":
            draw.ellipse((x0, y0, x1, y1), fill=ink)
        elif o["shape"] == "hline":
            top = y0 + (inner.height - line) // 2
            draw.rectangle((x0, top, x1, top + line - 1), fill=ink)
        else:
            left = x0 + (inner.width - line) // 2
            draw.rectangle((left, y0, left + line - 1, y1), fill=ink)

    def _image_value(self, block: Block, value: Any) -> Image.Image | None:
        if value is None:
            value = block.options["image"]
        if value is None:
            return None
        if isinstance(value, Image.Image):
            return value
        if isinstance(value, (str, Path)):
            with Image.open(value) as img:
                img.load()
                return img.copy()
        raise LayoutError(f"block '{block.name}': expected a Pillow image or a file path")


def _fit_image(picture: Image.Image, inner: Box, o: dict, background: str, rng: random.Random):
    """Scale an image into ``inner``; return it and where to paste it in the block."""
    if picture.mode in ("RGBA", "LA", "P", "PA") or "transparency" in picture.info:
        picture = _flatten(picture, background)
    else:
        picture = picture.convert("RGB")
    w, h = picture.size
    fit = o["fit"]
    if fit == "stretch":
        scale_w, scale_h = inner.width / w, inner.height / h
    elif fit == "none":
        scale_w = scale_h = 1.0
    else:
        pick = min if fit == "contain" else max
        scale_w = scale_h = pick(inner.width / w, inner.height / h)
    new = (max(1, round(w * scale_w)), max(1, round(h * scale_h)))
    if new != picture.size:
        picture = picture.resize(new, Image.Resampling.LANCZOS)
    # The part that sticks out (fit "cover" or "none") is cut off; alignment says which side
    # is kept. The part that is too small is placed by the same alignment.
    ox, oy = rng.random(), rng.random()
    left = align_offset(picture.width - inner.width, o["align"], ox)
    top = align_offset(picture.height - inner.height, o["valign"], oy)
    w, h = min(picture.width, inner.width), min(picture.height, inner.height)
    picture = picture.crop((left, top, left + w, top + h))
    x = inner.x + align_offset(inner.width - w, o["align"], ox)
    y = inner.y + align_offset(inner.height - h, o["valign"], oy)
    return picture, (x, y)
