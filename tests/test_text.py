import pytest
from PIL import Image, ImageChops, ImageDraw

from epdlib import Layout, ScreenMode
from epdlib.text import SHRINK_STEPS, arrange, fit_text, line_height, load_font, size_for_height

from .conftest import column, text_block

TRICKY = ["jump fjord", "gjpqy", "Åsa Ölçü", "ffj", "Hello, World!", "jjjj ffff", "Wy"]


def ink_box(font_path, text, width, height, max_lines, align, valign, shrink=False):
    """Draw text the way a text block does, with a wide margin, and return the ink's box."""
    size = size_for_height(font_path, height // max_lines)
    fit = fit_text(font_path, size, text, width, height, max_lines, shrink, "…")
    margin = 200
    canvas = Image.new("L", (width + 2 * margin, height + 2 * margin), 255)
    draw = ImageDraw.Draw(canvas)
    for line in arrange(fit.font, fit.lines, width, height, align, valign):
        draw.text((margin + line.x, margin + line.baseline), line.text, font=fit.font, anchor="ls")
    box = ImageChops.invert(canvas).getbbox()
    assert box is not None, "nothing was drawn"
    return (box[0] - margin, box[1] - margin, box[2] - margin, box[3] - margin)


@pytest.mark.parametrize("text", TRICKY)
@pytest.mark.parametrize("align", ["left", "center", "right"])
@pytest.mark.parametrize("valign", ["top", "center", "bottom"])
@pytest.mark.parametrize("font", ["default", "italic"])
def test_ink_stays_inside_the_block(text, align, valign, font, italic_font):
    path = italic_font if font == "italic" else None
    width, height = 300, 80
    left, top, right, bottom = ink_box(path, text, width, height, 1, align, valign)
    assert left >= 0 and top >= 0, (left, top)
    assert right <= width and bottom <= height, (right, bottom)


@pytest.mark.parametrize("height", [12, 23, 50, 97, 200])
def test_ink_inside_at_many_sizes(height, italic_font):
    width = height * 6
    left, top, right, bottom = ink_box(italic_font, "fjgÅ jump", width, height, 1, "left", "top")
    assert left >= 0 and top >= 0 and right <= width and bottom <= height


def test_italic_left_overhang_is_not_cut(italic_font):
    """Old epdlib issue 14: italic letters were cut off at the left edge."""
    font = load_font(italic_font, 100)
    assert font.getbbox("jump", anchor="ls")[0] < 0  # the font really does reach left
    left, *_ = ink_box(italic_font, "jump", 600, 120, 1, "left", "center")
    assert left == 0


def test_size_for_height_uses_the_whole_height():
    for height in [10, 33, 100, 480]:
        size = size_for_height(None, height)
        assert line_height(load_font(None, size)) <= height
        assert line_height(load_font(None, size + 1)) > height


def prepared(**options):
    block = text_block("t", **options)
    return Layout(column(block)).prepare(400, 100, ScreenMode.gray(16))


def test_size_comes_from_block_not_text():
    page = prepared(max_lines=1)
    size = page.font_sizes["t"]
    for text in ["Hi", "A much longer piece of text that does not fit on one line"]:
        fit = fit_text(None, size, text, 400, 100, 1, False, "…")
        assert fit.font.size == size


def test_more_lines_means_smaller_font():
    assert prepared(max_lines=2).font_sizes["t"] < prepared(max_lines=1).font_sizes["t"]


def test_fixed_font_size_wins():
    """Old epdlib issue 58: a size set in the layout must be used."""
    assert prepared(font_size={"pixels": 24}).font_sizes["t"] == 24
    assert prepared(font_size=0.5).font_sizes["t"] == 50


def test_too_long_text_is_cut_with_ellipsis():
    fit = fit_text(None, 40, "one two three four five six seven", 200, 100, 2, False, "…")
    assert len(fit.lines) == 2
    assert fit.lines[-1].endswith("…")
    assert not fit.complete


def test_text_that_fits_is_not_cut():
    fit = fit_text(None, 20, "one two", 400, 100, 2, False, "…")
    assert fit.lines == ["one two"]
    assert fit.complete


def test_newlines_start_a_new_line():
    fit = fit_text(None, 20, "one\ntwo", 400, 100, 3, False, "…")
    assert fit.lines == ["one", "two"]


def test_long_word_is_broken():
    fit = fit_text(None, 30, "x" * 80, 200, 300, 10, False, "…")
    assert len(fit.lines) > 1
    assert "".join(fit.lines) == "x" * 80


def test_shrink_uses_only_fixed_steps():
    base = 50
    allowed = {round(base * s) for s in SHRINK_STEPS}
    texts = ["short", "a little longer text", "a much much longer text that needs to wrap " * 3]
    sizes = {fit_text(None, base, t, 300, 50, 1, True, "…").font.size for t in texts}
    assert sizes <= allowed
    assert len(sizes) > 1


def test_shrink_tries_full_size_first():
    fit = fit_text(None, 50, "short", 300, 50, 1, True, "…")
    assert fit.font.size == 50


def sample_page(**options):
    """A wide, short block: the height alone would give a font too large for the width."""
    return Layout(column(text_block("t", **options))).prepare(300, 150, ScreenMode.gray(16))


def test_sample_limits_size_by_width():
    without = sample_page().font_sizes["t"]
    with_sample = sample_page(sample="Wednesday 30 September").font_sizes["t"]
    assert with_sample < without
    fit = fit_text(None, with_sample, "Wednesday 30 September", 300, 150, 1, False, "…")
    assert fit.complete


def test_sample_never_makes_text_larger_than_the_height_allows():
    assert sample_page(sample=".").font_sizes["t"] == sample_page().font_sizes["t"]


def test_fixed_text_is_used_as_sample():
    label = "Relative humidity"
    assert sample_page(text=label).font_sizes["t"] == sample_page(sample=label).font_sizes["t"]


def test_size_with_sample_does_not_depend_on_real_text():
    page = sample_page(sample="88:88")
    size = page.font_sizes["t"]
    for value in ["1:05", "12:47", "88:88"]:
        assert fit_text(None, size, value, 300, 150, 1, False, "…").font.size == size
