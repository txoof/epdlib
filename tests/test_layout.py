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


@pytest.mark.parametrize("axis", ["align", "valign"])
def test_random_alignment_moves_text_and_stays_inside(axis):
    block = text_block("a", font_size={"pixels": 20}, **{axis: "random"})
    page = Layout(column(block)).prepare(400, 200, MODE)
    boxes = {ink(page.render({"a": "x"}, seed=s)) for s in range(8)}
    assert len(boxes) > 1
    for box in boxes:
        assert box[0] >= 0 and box[1] >= 0 and box[2] <= 400 and box[3] <= 200


def test_random_alignment_moves_images():
    page = image_page(fit="none", align="random", valign="random")
    boxes = {ink(page.render({"img": black(20, 20)}, seed=s)) for s in range(8)}
    assert len(boxes) > 1
    assert all(b[2] - b[0] == 20 and b[3] - b[1] == 20 for b in boxes)


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


def test_content_size_is_inside_border_and_padding():
    page = image_page(padding={"pixels": 5}, border={"pixels": 2})
    assert page.content_size("img") == (186, 86)


def test_content_size_of_block_smaller_than_padding_is_zero():
    assert image_page(padding={"pixels": 60}).content_size("img") == (80, 0)


def test_content_size_unknown_block_is_an_error():
    with pytest.raises(LayoutError, match="no block named 'imgg'"):
        image_page().content_size("imgg")


@pytest.mark.parametrize("fit", ["contain", "cover", "stretch", "none"])
def test_picture_at_content_size_is_not_resized(fit):
    """A drawn picture at content_size is shown pixel for pixel, with any fit."""
    page = image_page(fit=fit, padding={"pixels": 5}, border={"pixels": 2})
    w, h = page.content_size("img")
    picture = Image.new("L", (w, h), "white")
    picture.putpixel((0, 0), 0)  # one black pixel in each corner
    picture.putpixel((w - 1, h - 1), 0)
    shown = page.render({"img": picture}).crop((7, 7, 7 + w, 7 + h))
    assert ImageChops.difference(shown, picture).getbbox() is None


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


def test_ellipse_fills_block():
    assert ink(shape_page("ellipse").render()) == (0, 0, 100, 50)


@pytest.mark.parametrize("shape", ["circle", "square"])
@pytest.mark.parametrize("size", [(100, 50), (50, 100), (264, 80)])
def test_circle_and_square_keep_their_shape_in_any_block(shape, size):
    block = {"name": "s", "type": "shape", "shape": shape}
    box = ink(Layout(column(block)).prepare(*size, MODE).render())
    assert box[2] - box[0] == box[3] - box[1] == min(size)


def test_circle_alignment():
    block = {"name": "s", "type": "shape", "shape": "circle", "align": "right"}
    assert ink(Layout(column(block)).prepare(100, 50, MODE).render()) == (50, 0, 100, 50)


def test_shape_colour_can_change_while_running():
    page = shape_page("rectangle")
    assert page.render({"s": {"fill": "white"}}).getpixel((50, 25)) == 255
    assert page.render({"s": {"background": "black", "fill": "black"}}).getpixel((0, 0)) == 0


def test_shape_bad_value():
    with pytest.raises(LayoutError, match="'fill' and/or 'background'"):
        shape_page("rectangle").render({"s": "red"})
    with pytest.raises(LayoutError, match="block 's': 'fill' 'blurple' is not a colour"):
        shape_page("rectangle").render({"s": {"fill": "blurple"}})


def test_huge_image_file_is_refused(tmp_path, monkeypatch):
    from epdlib import layout as layout_module

    monkeypatch.setattr(layout_module, "MAX_IMAGE_PIXELS", 100)
    path = tmp_path / "big.png"
    black(20, 20).save(path)
    with pytest.raises(LayoutError, match="block 'img': image is 20x20 pixels"):
        image_page().render({"img": str(path)})


def test_broken_image_file_gives_layout_error(tmp_path):
    path = tmp_path / "broken.png"
    path.write_bytes(b"not a picture")
    with pytest.raises(LayoutError, match="block 'img': could not draw it"):
        image_page().render({"img": str(path)})


def test_image_with_transparent_colour_gets_background():
    picture = black(20, 20).convert("P")
    picture.info["transparency"] = 0
    assert ink(image_page().render({"img": picture})) is None


def test_block_smaller_than_padding_is_skipped_quietly():
    page = Layout(row(text_block("a", padding={"pixels": 30}))).prepare(40, 40, MODE)
    assert page.render({"a": "x"}).size == (40, 40)


def test_gray_shape_stays_visible_on_black_and_white_screen():
    block = {"name": "s", "type": "shape", "fill": "gray"}
    image = Layout(column(block)).prepare(40, 40, ScreenMode.bw()).render().convert("L")
    assert {c for _, c in image.getcolors()} == {0, 255}


def text_page(width=200, height=50, **options):
    return Layout(column(text_block("a", **options))).prepare(width, height, MODE)


def test_text_fit_short_text_fits():
    page = text_page()
    report = page.text_fit("a", "Hi")
    assert report.complete
    assert not report.shrunk
    assert report.scale == 1.0
    assert report.size == page.font_sizes["a"]
    assert report.lines == ("Hi",)


def test_text_fit_reports_cut_text():
    report = text_page().text_fit("a", "a text that is much too long for this small block")
    assert not report.complete
    assert not report.shrunk
    assert len(report.lines) == 1
    assert report.lines[-1].endswith("…")


def test_text_fit_reports_shrunk_text():
    page = text_page(shrink=True)
    report = page.text_fit("a", "a little too long here")
    assert report.shrunk
    assert report.scale in (0.8, 0.6)
    assert report.size < page.font_sizes["a"]


def test_text_fit_without_value_uses_the_layout_text():
    assert text_page(text="Label").text_fit("a").lines == ("Label",)


def test_text_fit_of_block_with_no_room():
    page = text_page(padding={"pixels": 30})
    assert not page.text_fit("a", "Hi").complete
    assert page.text_fit("a", "").complete


def test_text_fit_changes_nothing():
    page = text_page(shrink=True)
    before = page.render({"a": "a little too long here"})
    page.text_fit("a", "x")
    after = page.render({"a": "a little too long here"})
    assert ImageChops.difference(before, after).getbbox() is None


def test_text_fit_needs_a_text_block():
    with pytest.raises(LayoutError, match=r"'img' is not a text block \(it is image\)"):
        image_page().text_fit("img")
    with pytest.raises(LayoutError, match="no block named 'b'"):
        text_page().text_fit("b")
