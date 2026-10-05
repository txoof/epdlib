import pytest
from PIL import Image, ImageChops

from epdlib import Layout, LayoutError, ScreenMode

from .conftest import column, row, text_block

MODE = ScreenMode.gray(16)


def test_render_returns_screen_sized_image():
    image = Layout(column(text_block("a"))).prepare(250, 122, MODE).render({"a": "Hi"})
    assert image.size == (250, 122)
    assert image.mode == "L"


def test_unknown_data_key_is_an_error():
    page = Layout(column(text_block("title"))).prepare(100, 50, MODE)
    with pytest.raises(LayoutError, match="no block named 'titel'"):
        page.render({"titel": "x"})


def test_default_text_from_layout():
    page = Layout(column(text_block("a", text="Label"))).prepare(200, 50, MODE)
    assert ImageChops.invert(page.render()).getbbox() is not None


def test_empty_block_is_blank():
    page = Layout(column(text_block("a"))).prepare(200, 50, MODE)
    assert ImageChops.invert(page.render()).getbbox() is None


def test_numbers_are_shown_as_text():
    page = Layout(column(text_block("a"))).prepare(200, 50, MODE)
    assert page.render({"a": 21.5}) == page.render({"a": "21.5"})


def test_inverse_swaps_colours():
    page = Layout(column(text_block("a", inverse=True))).prepare(100, 50, MODE)
    assert page.render().getpixel((0, 0)) == 0


def test_border_is_drawn_at_the_edge():
    page = Layout(column(text_block("a", border={"pixels": 3}))).prepare(100, 50, MODE)
    image = page.render()
    assert image.getpixel((0, 25)) == 0
    assert image.getpixel((2, 25)) == 0
    assert image.getpixel((3, 25)) == 255


def test_random_alignment_is_repeatable_with_seed():
    page = Layout(column(text_block("a", align="random", valign="random"))).prepare(400, 200, MODE)
    page_small = Layout(column(text_block("a", align="random", font_size={"pixels": 20})))
    page_small = page_small.prepare(400, 200, MODE)
    assert page.render({"a": "x"}, seed=1) == page.render({"a": "x"}, seed=1)
    images = {page_small.render({"a": "x"}, seed=s).tobytes() for s in range(5)}
    assert len(images) > 1


# Image blocks


def image_page(**options):
    return Layout(column({"name": "img", "type": "image", **options})).prepare(200, 100, MODE)


def black(w, h):
    return Image.new("RGB", (w, h), "black")


def ink(image):
    return ImageChops.invert(image).getbbox()


def test_image_contain_keeps_shape_and_centres():
    assert ink(image_page().render({"img": black(50, 50)})) == (50, 0, 150, 100)


@pytest.mark.parametrize(
    ("align", "valign", "box"),
    [
        ("left", "top", (0, 0, 50, 50)),
        ("right", "bottom", (150, 50, 200, 100)),
        ("center", "top", (75, 0, 125, 50)),
    ],
)
def test_image_alignment(align, valign, box):
    """Old epdlib issue 23: align images left/right/top/bottom."""
    page = image_page(fit="none", align=align, valign=valign)
    assert ink(page.render({"img": black(50, 50)})) == box


def test_image_cover_fills_block():
    assert ink(image_page(fit="cover").render({"img": black(50, 50)})) == (0, 0, 200, 100)


def test_image_stretch_fills_block():
    assert ink(image_page(fit="stretch").render({"img": black(10, 70)})) == (0, 0, 200, 100)


def test_transparent_image_gets_block_background():
    clear = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
    assert ink(image_page().render({"img": clear})) is None


def test_image_from_path(tmp_path):
    path = tmp_path / "x.png"
    black(20, 20).save(path)
    assert ink(image_page().render({"img": str(path)})) is not None


def test_bad_image_value():
    with pytest.raises(LayoutError, match="expected a Pillow image"):
        image_page().render({"img": 42})


# Shape blocks


def shape_page(shape, **options):
    block = {"name": "s", "type": "shape", "shape": shape, **options}
    return Layout(column(block)).prepare(100, 50, MODE)


def test_rectangle_fills_inside_padding():
    assert ink(shape_page("rectangle", padding={"pixels": 5}).render()) == (5, 5, 95, 45)


def test_hline_is_centred():
    assert ink(shape_page("hline", line_width={"pixels": 2}).render()) == (0, 24, 100, 26)


def test_vline_is_centred():
    assert ink(shape_page("vline", line_width={"pixels": 4}).render()) == (48, 0, 52, 50)


def test_ellipse():
    assert ink(shape_page("ellipse").render()) == (0, 0, 100, 50)


def test_shape_colour_can_change_while_running():
    page = shape_page("rectangle")
    assert page.render({"s": {"fill": "white"}}).getpixel((50, 25)) == 255
    assert page.render({"s": {"background": "black", "fill": "black"}}).getpixel((0, 0)) == 0


def test_shape_bad_value():
    with pytest.raises(LayoutError, match="'fill' and/or 'background'"):
        shape_page("rectangle").render({"s": "red"})


def test_block_smaller_than_padding_is_skipped_quietly():
    page = Layout(row(text_block("a", padding={"pixels": 30}))).prepare(40, 40, MODE)
    assert page.render({"a": "x"}).size == (40, 40)


def test_gray_shape_stays_visible_on_black_and_white_screen():
    block = {"name": "s", "type": "shape", "fill": "gray"}
    image = Layout(column(block)).prepare(40, 40, ScreenMode.bw()).render().convert("L")
    assert {c for _, c in image.getcolors()} == {0, 255}
