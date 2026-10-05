"""Measuring, wrapping and placing text.

Rules (see ``docs/text-size.md``):

- Every measurement and every drawing call uses the same reference point: the left end
  of the line the text sits on (the "baseline"; Pillow anchor ``ls``). What is measured is
  exactly what is drawn.
- The height of a line is the font's ascent (how far the tallest letters reach above the
  baseline) plus its descent (how far letters such as g and y reach below it). It is the
  same for every line, whatever letters are in it.
- The width of a line is its real ink, including letters that reach left of the start
  (italic f and j) or past the end.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

from .geometry import align_offset

FontType = ImageFont.FreeTypeFont

#: The steps a ``shrink: true`` block may use, as a share of its normal font size.
SHRINK_STEPS = (1.0, 0.8, 0.6)


#: The font used when a block does not name one: DejaVu Sans, which covers most
#: European scripts. Its licence is in the same folder.
DEFAULT_FONT = str(Path(__file__).parent / "fonts" / "DejaVuSans.ttf")


@lru_cache(maxsize=256)
def load_font(path: str | None, size: int) -> FontType:
    """Load a font at ``size`` pixels; ``None`` is :data:`DEFAULT_FONT`. Results are kept."""
    return ImageFont.truetype(path or DEFAULT_FONT, size)


def line_height(font: FontType) -> int:
    ascent, descent = font.getmetrics()
    return ascent + descent


def size_for_height(path: str | None, height: int) -> int:
    """The largest font size whose line height fits in ``height`` pixels (at least 1)."""
    if height < 1:
        return 1
    # Line height grows almost exactly in step with font size: estimate, then check nearby.
    ref = 1000
    guess = max(1, int(height * ref / line_height(load_font(path, ref))))
    size = guess + 1
    while size > 1 and line_height(load_font(path, size)) > height:
        size -= 1
    return size


def size_for_sample(path: str | None, largest: int, sample: str, width: int, lines: int) -> int:
    """The largest size up to ``largest`` at which ``sample`` fits in ``lines`` lines."""
    low, high = 1, largest
    while low < high:
        mid = (low + high + 1) // 2
        if wrap(load_font(path, mid), sample, width, lines, "")[1]:
            low = mid
        else:
            high = mid - 1
    return low


@dataclass(frozen=True)
class Extent:
    """Ink of one line, relative to the start of its baseline."""

    left: int
    right: int
    top: int  # negative: above the baseline
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left


def extent(font: FontType, text: str) -> Extent:
    """Where a line's ink reaches, also counting the normal space a line takes.

    The box covers both the ink and the font's normal line box (from 0 to the text's
    advance width, ascent above to descent below), so that spaces and empty lines count.
    """
    ascent, descent = font.getmetrics()
    if not text:
        return Extent(0, 0, -ascent, descent)
    x0, y0, x1, y1 = font.getbbox(text, anchor="ls")
    advance = font.getlength(text)
    return Extent(
        left=min(0, x0),
        right=max(int(-(-advance // 1)), x1),
        top=min(-ascent, y0),
        bottom=max(descent, y1),
    )


def fits(font: FontType, text: str, width: int) -> bool:
    return extent(font, text).width <= width


def wrap(
    font: FontType, text: str, width: int, max_lines: int, ellipsis: str
) -> tuple[list[str], bool]:
    """Break ``text`` into at most ``max_lines`` lines that fit ``width`` pixels.

    Returns the lines and whether all of the text fitted. When it did not, the last line
    ends with ``ellipsis``.
    """
    lines: list[str] = []
    for paragraph in text.split("\n"):
        lines.extend(_wrap_paragraph(font, paragraph, width, max_lines - len(lines)))
        if len(lines) > max_lines:
            break
    if len(lines) <= max_lines:
        return lines, True
    kept = lines[:max_lines]
    kept[-1] = _cut(font, kept[-1], width, ellipsis)
    return kept, False


def _wrap_paragraph(font: FontType, paragraph: str, width: int, limit: int) -> list[str]:
    """Wrap one paragraph. Stops once it has more than ``limit`` lines: the rest is cut."""
    # Quick method: measure each word once and add up the widths. Letter pairs that the
    # font spaces closer or wider (kerning) can make a line slightly wider than the sum,
    # so each line is checked once; if one does not fit, use the slow exact method.
    lines = _wrap_words(font, paragraph, width, limit, exact=False)
    if all(fits(font, line, width) for line in lines):
        return lines
    return _wrap_words(font, paragraph, width, limit, exact=True)


def _wrap_words(
    font: FontType, paragraph: str, width: int, limit: int, *, exact: bool
) -> list[str]:
    space = font.getlength(" ")
    lines: list[str] = []
    current = ""
    length = 0.0  # advance width of `current`
    for word in paragraph.split(" "):
        if current:
            new_length = length + space + font.getlength(word)
            if exact:
                ok = fits(font, f"{current} {word}", width)
            else:
                ok = new_length + _overhang(font, current[0], word[-1:] or " ") <= width
            if ok:
                current = f"{current} {word}"
                length = new_length
                continue
            lines.append(current)
            if len(lines) > limit:
                return lines
        # A word that is wider than the whole line is broken between letters.
        while word and not fits(font, word, width):
            n = _longest_prefix(font, word, width)
            lines.append(word[:n])
            word = word[n:]
            if len(lines) > limit:
                return lines
        current = word
        length = font.getlength(word)
    lines.append(current)
    return lines


@lru_cache(maxsize=4096)
def _overhang(font: FontType, first: str, last: str) -> int:
    """How far ink reaches left of the first letter and right of the last letter's width."""
    left = -min(0, font.getbbox(first, anchor="ls")[0])
    right = max(0, font.getbbox(last, anchor="ls")[2] - int(-(-font.getlength(last) // 1)))
    return left + right


def _longest_prefix(font: FontType, text: str, width: int, suffix: str = "") -> int:
    """How many leading characters of ``text`` (plus ``suffix``) fit; at least 1."""
    low, high = 0, len(text)
    while low < high:
        mid = (low + high + 1) // 2
        if fits(font, text[:mid] + suffix, width):
            low = mid
        else:
            high = mid - 1
    return max(low, 1) if not suffix else low


def _cut(font: FontType, line: str, width: int, ellipsis: str) -> str:
    n = _longest_prefix(font, line, width, ellipsis)
    return line[:n].rstrip() + ellipsis


@dataclass(frozen=True)
class PlacedLine:
    text: str
    x: int  # where to draw, with anchor "ls"
    baseline: int


def arrange(
    font: FontType,
    lines: list[str],
    width: int,
    height: int,
    align: str,
    valign: str,
    offset: tuple[float, float] = (0.5, 0.5),
) -> list[PlacedLine]:
    """Place lines inside a ``width`` x ``height`` area.

    ``offset`` is used for ``random`` alignment: 0 puts the text at the start, 1 at the end.
    """
    ascent, descent = font.getmetrics()
    step = ascent + descent
    extents = [extent(font, line) for line in lines]
    top = extents[0].top
    bottom = (len(lines) - 1) * step + extents[-1].bottom
    block_height = bottom - top
    y0 = align_offset(height - block_height, valign, offset[1]) - top
    placed = []
    for i, (line, ext) in enumerate(zip(lines, extents, strict=True)):
        x = align_offset(width - ext.width, align, offset[0]) - ext.left
        placed.append(PlacedLine(line, x, y0 + i * step))
    return placed


@dataclass(frozen=True)
class TextFit:
    font: FontType
    lines: list[str]
    complete: bool


def fit_text(
    path: str | None,
    base_size: int,
    text: str,
    width: int,
    height: int,
    max_lines: int,
    shrink: bool,
    ellipsis: str,
) -> TextFit:
    """Wrap ``text`` at ``base_size``; with ``shrink``, try the smaller fixed steps too.

    A smaller step may use more lines than ``max_lines`` when they fit in ``height``.
    """
    steps = SHRINK_STEPS if shrink else (1.0,)
    result = None
    for step in steps:
        font = load_font(path, max(1, round(base_size * step)))
        allowed = max(max_lines, height // line_height(font)) if step < 1 else max_lines
        lines, complete = wrap(font, text, width, allowed, ellipsis)
        result = TextFit(font, lines, complete)
        if complete:
            break
    assert result is not None
    return result
