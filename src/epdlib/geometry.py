"""Working out where each block goes.

Each row or column gives its fixed-size items (``pixels``) their space first, then shares
the rest between the other items by their ``size``. Positions are rounded so that the
items always fill the space exactly: no gaps and no overlaps from rounding.
"""

from __future__ import annotations

from dataclasses import dataclass

from .spec import Block, Container, LayoutError, Node


@dataclass(frozen=True)
class Box:
    """A rectangle on the screen, in pixels."""

    x: int
    y: int
    width: int
    height: int

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    def inset(self, amount: int) -> Box:
        """The box made smaller by ``amount`` pixels on every side (never below zero)."""
        w = max(0, self.width - 2 * amount)
        h = max(0, self.height - 2 * amount)
        return Box(
            self.x + min(amount, self.width // 2), self.y + min(amount, self.height // 2), w, h
        )


def align_offset(spare: int, how: str, offset: float = 0.5) -> int:
    """Where to start something in ``spare`` pixels of free space.

    ``how`` is left/top, center, right/bottom, or random (then ``offset``, 0 to 1, is used).
    No free space (zero or less) always gives 0.
    """
    spare = max(spare, 0)
    if how in ("left", "top"):
        return 0
    if how in ("right", "bottom"):
        return spare
    if how == "random":
        return round(spare * offset)
    return spare // 2


def place(root: Container, width: int, height: int) -> dict[str, Box]:
    """Return the box of every block for a screen of ``width`` x ``height`` pixels."""
    if width <= 0 or height <= 0:
        raise LayoutError(f"screen size must be above zero, got {width}x{height}")
    short = min(width, height)
    boxes: dict[str, Box] = {}
    _place(root, Box(0, 0, width, height), short, boxes)
    return boxes


def _place(node: Node, box: Box, short: int, boxes: dict[str, Box]) -> None:
    pad = node.padding.to_pixels(short)
    if isinstance(node, Block):
        # A block's padding is kept inside its box: the block draws its own background there.
        boxes[node.name] = box
        return
    assert isinstance(node, Container)
    inner = box.inset(pad)
    horizontal = node.direction == "row"
    length = inner.width if horizontal else inner.height
    gap = node.gap.to_pixels(short)
    spans = split(node, length, gap)
    for child, (start, span) in zip(node.children, spans, strict=True):
        if horizontal:
            child_box = Box(inner.x + start, inner.y, span, inner.height)
        else:
            child_box = Box(inner.x, inner.y + start, inner.width, span)
        _place(child, child_box, short, boxes)


def split(node: Container, length: int, gap: int) -> list[tuple[int, int]]:
    """Divide ``length`` pixels between a container's children: (start, length) for each."""
    children = node.children
    gaps = gap * (len(children) - 1)
    fixed = sum(c.pixels for c in children if c.pixels is not None)
    free = length - fixed - gaps
    if free < 0:
        names = ", ".join(_label(c) for c in children if c.pixels is not None)
        raise LayoutError(
            f"{node.where}: fixed sizes ({fixed} px for {names}) plus gaps ({gaps} px) need "
            f"more than the {length} px available"
        )
    total_share = sum(c.size for c in children if c.size is not None)
    spans: list[tuple[int, int]] = []
    pos = 0
    share_done = 0.0
    used_by_shares = 0
    for i, child in enumerate(children):
        if child.pixels is not None:
            span = child.pixels
        else:
            # Round the running total, not each item, so the shares always add up to `free`.
            share_done += child.size or 0
            end = round(free * share_done / total_share) if total_share else 0
            span = end - used_by_shares
            used_by_shares = end
        spans.append((pos, span))
        pos += span + (gap if i < len(children) - 1 else 0)
    return spans


def _label(node: Node) -> str:
    return f"'{node.name}'" if isinstance(node, Block) else node.where
