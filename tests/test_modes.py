import pytest
from PIL import Image, ImageColor

from epdlib import SEVEN_COLORS, Layout, ScreenMode

from .conftest import column, row, text_block

GRADIENT = Image.linear_gradient("L").resize((120, 80)).convert("RGB")
LAYOUT = Layout(
    row(
        text_block("label", text="Jumping fox", fill="red", rgb_support=True),
        {"name": "photo", "type": "image", "rgb_support": True},
        text_block("plain", text="Gray text", fill="red"),
    )
)


def render(mode):
    return LAYOUT.prepare(360, 80, mode).render({"photo": GRADIENT})


def colors(image):
    return {c for _, c in image.getcolors(maxcolors=1 << 24)}


def test_bw_has_two_values():
    image = render(ScreenMode.bw())
    assert image.mode == "1"
    assert colors(image.convert("L")) <= {0, 255}


@pytest.mark.parametrize("levels", [4, 16])
def test_gray_uses_only_its_levels(levels):
    image = render(ScreenMode.gray(levels))
    assert image.mode == "L"
    steps = {round(i * 255 / (levels - 1)) for i in range(levels)}
    assert colors(image) <= steps


def test_palette_uses_only_its_colors():
    image = render(ScreenMode.palette())
    allowed = {ImageColor.getrgb(c) for c in SEVEN_COLORS}
    assert image.mode == "RGB"
    assert colors(image) <= allowed


def test_rgb_support_block_keeps_colour_on_colour_screens():
    image = LAYOUT.prepare(360, 80, ScreenMode.rgb()).render({"photo": GRADIENT})
    label = image.crop((0, 0, 120, 80))
    assert (255, 0, 0) in colors(label)


def test_block_without_rgb_support_is_gray_on_full_colour_screen():
    image = LAYOUT.prepare(360, 80, ScreenMode.rgb()).render({"photo": GRADIENT})
    plain = image.crop((240, 0, 360, 80))
    assert all(r == g == b for r, g, b in colors(plain))
    assert len(colors(plain)) > 2  # anti-aliased text edges in gray


def test_block_without_rgb_support_is_black_and_white_on_palette_screen():
    image = render(ScreenMode.palette())
    plain = image.crop((240, 0, 360, 80))
    assert colors(plain) <= {(0, 0, 0), (255, 255, 255)}


def test_text_is_never_dithered():
    """Text on a 4-level screen: each pixel goes to the nearest level, no dot patterns.

    A dithered white background would contain dark pixels; undithered it is pure white.
    """
    block = text_block("t", text="Hello", background="#f0f0f0", font_size={"pixels": 10})
    image = Layout(column(block)).prepare(200, 50, ScreenMode.gray(4)).render()
    corner = image.crop((150, 0, 200, 50))  # right of the short text: background only
    assert colors(corner) == {255}


def changes_along_row(image, y):
    row = [image.getpixel((x, y)) for x in range(image.width)]
    return sum(1 for a, b in zip(row, row[1:], strict=False) if a != b)


def test_images_are_dithered():
    """A smooth gradient shown in black and white becomes a dot pattern.

    Without dithering, each row would be all black or all white (no changes along it).
    """
    image = render(ScreenMode.bw()).convert("L")
    photo = image.crop((130, 30, 230, 50))  # middle of the gradient
    assert changes_along_row(photo, 10) > 10


def test_convert_any_image():
    rgba = Image.new("RGBA", (10, 10), (255, 0, 0, 0))
    out = ScreenMode.gray(16).convert(rgba)
    assert out.mode == "L"
    assert colors(out) == {255}  # transparent -> white background


def test_palette_must_have_black_and_white():
    with pytest.raises(ValueError, match="black and white"):
        ScreenMode.palette(("red", "white"))


def test_gray_levels_checked():
    with pytest.raises(ValueError):
        ScreenMode.gray(1)
