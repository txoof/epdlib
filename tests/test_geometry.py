import pytest

from epdlib import Box, Layout, LayoutError, ScreenMode

from .conftest import column, row, text_block


def boxes(data, width=800, height=480):
    return Layout(data).prepare(width, height, ScreenMode.bw()).boxes


def test_shares_split_the_space():
    b = boxes(column(text_block("top", size=1), text_block("bottom", size=3)))
    assert b["top"] == Box(0, 0, 800, 120)
    assert b["bottom"] == Box(0, 120, 800, 360)


def test_sizes_need_not_add_up_to_one():
    a = boxes(row(text_block("l", size=37), text_block("r", size=63)))
    b = boxes(row(text_block("l", size=0.37), text_block("r", size=0.63)))
    assert a == b


def test_nested_rows_and_columns():
    b = boxes(
        column(
            text_block("title", size=1),
            row(text_block("body", size=3), text_block("art", size=2), size=4),
        )
    )
    assert b["title"] == Box(0, 0, 800, 96)
    assert b["body"] == Box(0, 96, 480, 384)
    assert b["art"] == Box(480, 96, 320, 384)


def test_fixed_pixels_are_taken_first():
    b = boxes(column(text_block("a"), text_block("line", pixels=2), text_block("b")))
    assert b["line"].height == 2
    assert b["a"].height + b["b"].height == 478


def test_gap_and_padding():
    b = boxes(row(text_block("a"), text_block("b"), gap={"pixels": 10}, padding={"pixels": 5}))
    assert b["a"] == Box(5, 5, 390, 470)
    assert b["b"] == Box(405, 5, 390, 470)


def test_gap_scales_with_screen():
    small = boxes(row(text_block("a"), text_block("b"), gap=0.1), 200, 100)
    big = boxes(row(text_block("a"), text_block("b"), gap=0.1), 2000, 1000)
    assert small["b"].x - small["a"].width == 10
    assert big["b"].x - big["a"].width == 100


@pytest.mark.parametrize("width", [7, 99, 101, 799, 1201])
def test_rounding_never_leaves_gaps_or_overlaps(width):
    items = [text_block(str(i), size=s) for i, s in enumerate([1, 1, 1, 2, 3, 0.5, 7])]
    b = boxes(row(*items), width, 50)
    x = 0
    for i in range(len(items)):
        assert b[str(i)].x == x
        x += b[str(i)].width
    assert x == width


def test_fixed_sizes_too_large_names_them():
    data = column(text_block("a", pixels=300), text_block("b", pixels=300))
    with pytest.raises(LayoutError, match=r"fixed sizes \(600 px for 'a', 'b'\)"):
        boxes(data)


def test_works_on_any_screen_shape():
    data = column(text_block("title", size=1), row(text_block("l"), text_block("r"), size=4))
    for width, height in [(250, 122), (1200, 825), (480, 800)]:
        b = boxes(data, width, height)
        assert b["title"].width == width
        assert b["l"].width + b["r"].width == width
        assert b["title"].height + b["l"].height == height
