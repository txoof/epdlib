"""The three ways to dither (#94): photo (Floyd-Steinberg), pattern (Bayer 8x8), smooth
(Atkinson)."""

import pytest
from PIL import Image, ImageDraw

from epdlib import Layout, LayoutError, ScreenMode
from epdlib.modes import DITHERS

from .conftest import column

GRAY_MODES = {"bw": ScreenMode.bw()} | {
    f"gray{n}": ScreenMode.gray(n)
    for n in (3, 4, 5, 16, 255)  # 5, 255: levels not whole
}


def flat(value, size=(64, 32)):
    return Image.new("L", size, value)


def values(image):
    return {v for _, v in image.convert("L").getcolors()}


def white_share(image):
    hist = image.convert("L").histogram()
    return hist[255] / (image.width * image.height)


def tiles(image, box):
    """Every 8x8 tile inside ``box``, as bytes."""
    x0, y0, x1, y1 = box
    return {
        image.crop((x, y, x + 8, y + 8)).tobytes()
        for y in range(y0, y1 - 7, 8)
        for x in range(x0, x1 - 7, 8)
    }


def gray_bar_page():
    """The page from the 7.5" screen test where Floyd-Steinberg slipped a row (#94)."""
    page = Image.new("L", (800, 480), 255)
    ImageDraw.Draw(page).rectangle((400, 48, 720, 96), fill=128)
    return page


def test_photo_slips_on_a_flat_gray_bar():
    """The problem itself: Floyd-Steinberg gives the bar more than one kind of tile."""
    out = ScreenMode.bw().convert(gray_bar_page())
    assert len(tiles(out.convert("L"), (400, 48, 720, 96))) > 2


def test_pattern_never_slips_on_a_flat_gray_bar():
    out = ScreenMode.bw().convert(gray_bar_page(), dither="pattern")
    assert len(tiles(out.convert("L"), (400, 48, 720, 96))) == 1


@pytest.mark.parametrize("value", [16, 64, 128, 192, 240])
def test_pattern_shade_matches_the_gray(value):
    out = ScreenMode.bw().reduce(flat(value), dither="pattern", color=False)
    assert white_share(out) == pytest.approx(value / 255, abs=1 / 64)


@pytest.mark.parametrize(
    ("levels", "value", "nearest"), [(4, 100, {85, 170}), (16, 128, {119, 136})]
)
def test_pattern_uses_the_two_nearest_grays(levels, value, nearest):
    out = ScreenMode.gray(levels).reduce(flat(value), dither="pattern", color=False)
    assert values(out) == nearest


def test_smooth_shades_keep_their_order():
    """Atkinson passes on only 6/8 of each error, so light grays come out a little
    lighter and dark grays a little darker; the middle stays the middle."""
    shares = []
    for value in (64, 128, 192):
        out = ScreenMode.bw().reduce(flat(value, (128, 128)), dither="smooth", color=False)
        assert values(out) == {0, 255}
        shares.append(white_share(out))
    assert shares[1] == pytest.approx(0.5, abs=0.03)
    assert shares[0] <= 64 / 255 and shares[2] >= 192 / 255


@pytest.mark.parametrize("value", [4, 12, 100, 128, 250])
def test_pattern_shade_matches_the_gray_on_16_grays(value):
    out = ScreenMode.gray(16).reduce(flat(value), dither="pattern", color=False)
    average = sum(i * n for i, n in enumerate(out.histogram())) / (out.width * out.height)
    assert average == pytest.approx(value, abs=1)


@pytest.mark.parametrize("value", [4, 12, 95])
def test_smooth_dithers_on_16_grays(value):
    """A gray between two of the 16 levels gets dots of both, even when it is close to one."""
    out = ScreenMode.gray(16).reduce(flat(value, (64, 64)), dither="smooth", color=False)
    assert len(values(out)) == 2
    average = sum(i * n for i, n in enumerate(out.histogram())) / (out.width * out.height)
    assert average == pytest.approx(value, abs=3)


@pytest.mark.parametrize("mode", GRAY_MODES)
@pytest.mark.parametrize("dither", DITHERS)
def test_every_method_uses_only_the_screen_levels(mode, dither):
    screen = GRAY_MODES[mode]
    gradient = Image.linear_gradient("L").resize((64, 64))
    out = screen.reduce(gradient, dither=dither, color=False)
    steps = {round(i * 255 / (screen.levels - 1)) for i in range(screen.levels)}
    assert values(out) <= steps


@pytest.mark.parametrize("mode", GRAY_MODES)
@pytest.mark.parametrize("dither", DITHERS)
def test_screen_levels_stay_solid(mode, dither):
    """A gray the screen can show needs no dots, whatever the method."""
    if (mode, dither) == ("gray255", "photo"):
        pytest.skip("Pillow's palette lookup is not exact with 255 entries (as before #94)")
    screen = GRAY_MODES[mode]
    for i in range(screen.levels):
        level = round(i * 255 / (screen.levels - 1))
        out = screen.reduce(flat(level), dither=dither, color=False)
        assert values(out) == {level}


@pytest.mark.parametrize("dither", ["pattern", "smooth"])
@pytest.mark.parametrize("measured", [False, True])
def test_colour_screens_use_photo_for_every_method(dither, measured):
    colours = ("#000000", "#ffffff", "#ff0000")
    panel = ((40, 40, 40), (230, 230, 220), (150, 30, 30))
    screen = ScreenMode.palette(colours, measured=panel if measured else ())
    picture = Image.linear_gradient("L").resize((64, 64)).convert("RGB")
    out = screen.reduce(picture, dither=dither, color=True)
    assert out.tobytes() == screen.reduce(picture, dither="photo", color=True).tobytes()


def test_block_without_colour_on_a_colour_screen_gets_the_pattern():
    out = ScreenMode.palette().reduce(flat(128), dither="pattern", color=False)
    assert len(tiles(out.convert("L"), (0, 0, 64, 32))) == 1


def test_full_colour_screen_is_not_dithered():
    picture = Image.linear_gradient("L").resize((64, 64))
    for dither in DITHERS:
        out = ScreenMode.rgb().reduce(picture, dither=dither, color=True)
        assert out.tobytes() == picture.convert("RGB").tobytes()


def test_unknown_dither_is_refused():
    with pytest.raises(ValueError, match="dither must be one of photo, pattern, smooth"):
        ScreenMode.bw().convert(flat(128), dither="fast")
    with pytest.raises(ValueError, match="dither must be one of"):
        ScreenMode.bw().reduce(flat(128), dither=True, color=False)


def image_layout(**options):
    return Layout(column({"name": "pic", "type": "image", "padding": 0, **options}))


@pytest.mark.parametrize("dither", DITHERS)
def test_image_block_dither_setting(dither):
    """The block gives exactly what ScreenMode.reduce gives for its dither choice."""
    picture = Image.linear_gradient("L").resize((64, 32))
    page = image_layout(dither=dither).prepare(64, 32, ScreenMode.bw())
    out = page.render({"pic": picture}).convert("L")
    expected = ScreenMode.bw().reduce(picture, dither=dither, color=False)
    assert out.tobytes() == expected.tobytes()


def test_the_three_methods_differ():
    picture = Image.linear_gradient("L").resize((64, 32))
    outs = {ScreenMode.bw().reduce(picture, dither=d, color=False).tobytes() for d in DITHERS}
    assert len(outs) == 3


def test_image_block_dither_default_is_photo():
    assert image_layout().blocks["pic"].options["dither"] == "photo"


def test_image_block_unknown_dither_is_an_error():
    with pytest.raises(LayoutError, match="dither"):
        image_layout(dither="fast")


def test_dither_is_only_for_image_blocks():
    shape = {"name": "bar", "type": "shape", "dither": "photo"}
    with pytest.raises(LayoutError, match="unknown key 'dither'"):
        Layout(column(shape))


def test_shape_blocks_use_the_pattern():
    layout = Layout(column({"name": "bar", "type": "shape", "fill": "gray", "padding": 0}))
    out = layout.prepare(320, 48, ScreenMode.bw()).render().convert("L")
    assert len(tiles(out, (0, 0, 320, 48))) == 1
