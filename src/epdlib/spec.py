"""Reading and checking layout descriptions.

A layout is plain data: dictionaries and lists. It is a tree of rows and columns, with
blocks at the ends. This module checks that data and turns it into the classes below, with
a clear error message that names the block when something is wrong.
"""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import ImageColor

#: Deepest allowed nesting of rows and columns.
MAX_DEPTH = 10
#: Largest layout file that :func:`read_json` reads, in bytes.
MAX_JSON_BYTES = 1_000_000
#: Largest fixed size in pixels anywhere in a layout.
MAX_PIXELS = 20_000

BLOCK_TYPES = ("text", "image", "shape")
SHAPES = ("rectangle", "square", "circle", "ellipse", "hline", "vline")
H_ALIGN = ("left", "center", "right", "random")
V_ALIGN = ("top", "center", "bottom", "random")
FITS = ("contain", "cover", "stretch", "none")

_COMMON = {"name", "type", "size", "pixels", "padding", "background", "fill", "border"}
_COMMON |= {"inverse", "rgb_support"}
_KEYS = {
    "text": _COMMON
    | {"text", "sample", "font", "font_size", "max_lines", "shrink", "align", "valign"}
    | {"ellipsis"},
    "image": _COMMON | {"image", "fit", "align", "valign"},
    "shape": _COMMON | {"shape", "line_width", "align", "valign"},
}
_CONTAINER_KEYS = {"row", "column", "size", "pixels", "gap", "padding"}
# Keys people often try, and the key they probably meant.
_HINTS = {"color": "fill", "colour": "fill", "font_color": "fill", "font_colour": "fill"}


class LayoutError(ValueError):
    """A layout description is not valid. The message says where and why."""


@dataclass(frozen=True)
class Length:
    """A length that is either a share of the screen's shorter side, or fixed pixels."""

    share: float = 0.0
    pixels: int | None = None

    def to_pixels(self, short_side: int) -> int:
        if self.pixels is not None:
            return self.pixels
        return round(self.share * short_side)


ZERO = Length()


@dataclass(frozen=True)
class Node:
    """Common part of blocks and containers: how much space it gets in its parent."""

    size: float | None  # share of the parent's free space; None when ``pixels`` is set
    pixels: int | None
    padding: Length
    where: str  # readable position in the layout, for error messages


@dataclass(frozen=True)
class Container(Node):
    direction: str  # "row" or "column"
    children: tuple[Node, ...]
    gap: Length


@dataclass(frozen=True)
class Block(Node):
    name: str
    type: str
    options: dict[str, Any] = field(default_factory=dict)


def parse(data: Any, *, asset_dirs: list[Path] | None = None) -> Container:
    """Check a layout and return its tree.

    ``asset_dirs``: when given, font and image paths must be inside one of these folders.
    Used for layouts from files that are not trusted code (see :func:`read_json`).
    """
    parser = _Parser(asset_dirs)
    if not isinstance(data, dict):
        raise LayoutError("layout: must be a dictionary with a 'row' or 'column' list")
    if "row" not in data and "column" not in data:
        raise LayoutError("layout: the top level must be a 'row' or a 'column'")
    root = parser.node(data, "layout", 1)
    if not isinstance(root, Container):
        raise LayoutError("layout: the top level must be a 'row' or a 'column'")
    return root


def read_json(source: str | Path) -> Any:
    """Read the data of a JSON layout file, with clear errors and a size limit.

    JSON files are read as data only. Pass the result to ``Layout(data, asset_dirs=...)``
    so that font and image paths are checked too (``Layout.from_json`` does both).
    """
    path = Path(source)
    try:
        with path.open("rb") as file:
            raw = file.read(MAX_JSON_BYTES + 1)
    except OSError as err:
        raise LayoutError(f"{path}: cannot read it: {err}") from None
    if len(raw) > MAX_JSON_BYTES:
        raise LayoutError(f"{path}: larger than {MAX_JSON_BYTES} bytes")
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, RecursionError) as err:
        # ValueError covers bad JSON, bad UTF-8 and numbers with thousands of digits.
        message = "nested too deeply" if isinstance(err, RecursionError) else err
        raise LayoutError(f"{path}: not valid JSON: {message}") from None


def blocks(root: Container) -> list[Block]:
    """All blocks in a layout, in order."""
    found: list[Block] = []
    for child in root.children:
        if isinstance(child, Block):
            found.append(child)
        else:
            found.extend(blocks(child))  # type: ignore[arg-type]
    return found


class _Parser:
    def __init__(self, asset_dirs: list[Path] | None):
        self.asset_dirs = [d.resolve() for d in asset_dirs] if asset_dirs is not None else None
        self.names: set[str] = set()

    def node(self, data: Any, where: str, depth: int) -> Node:
        if not isinstance(data, dict):
            raise LayoutError(f"{where}: must be a dictionary, got {type(data).__name__}")
        if "row" in data or "column" in data:
            if depth > MAX_DEPTH:
                raise LayoutError(f"{where}: rows and columns nested deeper than {MAX_DEPTH}")
            return self.container(data, where, depth)
        if "name" in data:
            return self.block(data, where)
        raise LayoutError(f"{where}: needs a 'name' (a block) or a 'row'/'column' list")

    def container(self, data: dict, where: str, depth: int) -> Container:
        if "row" in data and "column" in data:
            raise LayoutError(f"{where}: has both 'row' and 'column'; use one")
        _check_keys(data, _CONTAINER_KEYS, where)
        direction = "row" if "row" in data else "column"
        items = data[direction]
        if not isinstance(items, list) or not items:
            raise LayoutError(f"{where}: '{direction}' must be a list with at least one item")
        children = tuple(
            self.node(item, _child_where(item, f"{where}.{direction}[{i}]"), depth + 1)
            for i, item in enumerate(items)
        )
        size, pixels = _size(data, where)
        return Container(
            size=size,
            pixels=pixels,
            padding=_length(data.get("padding"), "padding", where),
            where=where,
            direction=direction,
            children=children,
            gap=_length(data.get("gap"), "gap", where),
        )

    def block(self, data: dict, where: str) -> Block:
        name = data["name"]
        if not isinstance(name, str) or not name:
            raise LayoutError(f"{where}: 'name' must be a non-empty string")
        if name in self.names:
            raise LayoutError(f"{where}: the name '{name}' is used twice")
        self.names.add(name)
        kind = data.get("type")
        if kind not in BLOCK_TYPES:
            raise LayoutError(f"{where}: 'type' must be one of {', '.join(BLOCK_TYPES)}")
        _check_keys(data, _KEYS[kind], where)
        size, pixels = _size(data, where)
        opts = self.options(kind, data, where)
        return Block(
            size=size,
            pixels=pixels,
            padding=_length(data.get("padding"), "padding", where),
            where=where,
            name=name,
            type=kind,
            options=opts,
        )

    def options(self, kind: str, data: dict, where: str) -> dict[str, Any]:
        o: dict[str, Any] = {
            "background": check_color(data.get("background", "white"), "background", where),
            "fill": check_color(data.get("fill", "black"), "fill", where),
            "border": _length(data.get("border"), "border", where),
            "inverse": _bool(data.get("inverse", False), "inverse", where),
            "rgb_support": _bool(data.get("rgb_support", False), "rgb_support", where),
        }
        if kind == "text":
            o["text"] = _str(data.get("text", ""), "text", where)
            o["sample"] = _str(data.get("sample", ""), "sample", where)
            o["font"] = self.path(data.get("font"), "font", where)
            fs = data.get("font_size")
            o["font_size"] = None if fs is None else _length(fs, "font_size", where)
            if o["font_size"] is not None and o["font_size"].to_pixels(1000) <= 0:
                raise LayoutError(f"{where}: 'font_size' must be more than 0")
            o["max_lines"] = _int(data.get("max_lines", 1), "max_lines", where, 1, 1000)
            o["shrink"] = _bool(data.get("shrink", False), "shrink", where)
            o["align"] = _choice(data.get("align", "left"), H_ALIGN, "align", where)
            o["valign"] = _choice(data.get("valign", "center"), V_ALIGN, "valign", where)
            o["ellipsis"] = _str(data.get("ellipsis", "…"), "ellipsis", where)
        elif kind == "image":
            o["image"] = self.path(data.get("image"), "image", where)
            o["fit"] = _choice(data.get("fit", "contain"), FITS, "fit", where)
            o["align"] = _choice(data.get("align", "center"), H_ALIGN, "align", where)
            o["valign"] = _choice(data.get("valign", "center"), V_ALIGN, "valign", where)
        else:
            o["shape"] = _choice(data.get("shape", "rectangle"), SHAPES, "shape", where)
            o["line_width"] = _length(data.get("line_width", {"pixels": 1}), "line_width", where)
            o["align"] = _choice(data.get("align", "center"), H_ALIGN, "align", where)
            o["valign"] = _choice(data.get("valign", "center"), V_ALIGN, "valign", where)
        return o

    def path(self, value: Any, key: str, where: str) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value:
            raise LayoutError(f"{where}: '{key}' must be a file path")
        if self.asset_dirs is None:
            return value
        # Relative paths are looked up in each allowed folder in turn. resolve() follows
        # ".." and links, so a path that leads out of the folder is refused.
        inside = False
        for d in self.asset_dirs:
            try:
                candidate = (d / value).resolve()
            except (OSError, ValueError):
                raise LayoutError(f"{where}: '{key}' {value!r} is not a valid path") from None
            if not candidate.is_relative_to(d):
                continue
            inside = True
            if candidate.is_file():
                return str(candidate)
        if not inside:
            raise LayoutError(f"{where}: '{key}' {value!r} is outside the allowed folders")
        raise LayoutError(f"{where}: '{key}' {value!r} is not a file in the allowed folders")


def _child_where(item: Any, fallback: str) -> str:
    if isinstance(item, dict) and isinstance(item.get("name"), str):
        return f"block '{item['name']}'"
    return fallback


def _check_keys(data: dict, allowed: set[str], where: str) -> None:
    for key in data:
        if key not in allowed:
            hint = [_HINTS[key]] if _HINTS.get(key) in allowed else []
            hint = hint or difflib.get_close_matches(str(key), allowed, n=1)
            extra = f" (did you mean '{hint[0]}'?)" if hint else ""
            raise LayoutError(f"{where}: unknown key '{key}'{extra}")


def _size(data: dict, where: str) -> tuple[float | None, int | None]:
    if "size" in data and "pixels" in data:
        raise LayoutError(f"{where}: has both 'size' and 'pixels'; use one")
    if "pixels" in data:
        return None, _int(data["pixels"], "pixels", where, 0, MAX_PIXELS)
    size = data.get("size", 1)
    if isinstance(size, bool) or not isinstance(size, (int, float)) or not size > 0:
        raise LayoutError(f"{where}: 'size' must be a number above 0, got {size!r}")
    if size > 1_000_000:
        raise LayoutError(f"{where}: 'size' is too large")
    return float(size), None


def _length(value: Any, key: str, where: str) -> Length:
    if value is None:
        return ZERO
    if isinstance(value, dict):
        _check_keys(value, {"pixels"}, f"{where} '{key}'")
        if "pixels" not in value:
            raise LayoutError(f"{where}: '{key}' must be a number or {{'pixels': n}}")
        return Length(pixels=_int(value["pixels"], key, where, 0, MAX_PIXELS))
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise LayoutError(
            f"{where}: '{key}' must be a share of the screen from 0 to 1, or {{'pixels': n}};"
            f" got {value!r}"
        )
    return Length(share=float(value))


def _int(value: Any, key: str, where: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise LayoutError(f"{where}: '{key}' must be a whole number from {low} to {high}")
    return value


def _bool(value: Any, key: str, where: str) -> bool:
    if not isinstance(value, bool):
        raise LayoutError(f"{where}: '{key}' must be true or false")
    return value


def _str(value: Any, key: str, where: str) -> str:
    if not isinstance(value, str):
        raise LayoutError(f"{where}: '{key}' must be text")
    return value


def _choice(value: Any, choices: tuple[str, ...], key: str, where: str) -> str:
    if value not in choices:
        raise LayoutError(f"{where}: '{key}' must be one of {', '.join(choices)}")
    return value


def check_color(value: Any, key: str, where: str) -> str:
    """Return ``value`` if it is a colour name or ``#rrggbb``; raise :class:`LayoutError` if not."""
    try:
        ImageColor.getrgb(value)
    except (ValueError, AttributeError, TypeError):
        raise LayoutError(f"{where}: '{key}' {value!r} is not a colour name or #rrggbb") from None
    return value
