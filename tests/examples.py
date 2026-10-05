"""Example layouts used by the image tests. Also a starting point for the docs gallery."""

from pathlib import Path

from PIL import Image, ImageDraw

FONTS = Path(__file__).parent / "fonts"


def photo(width=300, height=200) -> Image.Image:
    """A made-up colour picture: sky, sun and hills, so no image files are needed."""
    image = Image.new("RGB", (width, height), "#7ec8f0")
    draw = ImageDraw.Draw(image)
    for y in range(height // 2):
        shade = 200 + y * 55 // (height // 2)
        draw.line((0, y, width, y), fill=(120, 190, shade))
    draw.ellipse((width * 0.65, height * 0.1, width * 0.85, height * 0.4), fill="#ffd23f")
    draw.polygon([(0, height), (width * 0.3, height * 0.5), (width * 0.6, height)], fill="#3a7d44")
    draw.polygon(
        [(width * 0.4, height), (width * 0.75, height * 0.55), (width, height)], fill="#255c2f"
    )
    return image


EXAMPLES = {
    # Title, divider, then text next to a picture.
    "article": (
        {
            "padding": 0.02,
            "gap": 0.02,
            "column": [
                {"name": "title", "type": "text", "size": 1, "align": "center"},
                {"name": "rule", "type": "shape", "shape": "hline", "pixels": 3},
                {
                    "size": 4,
                    "gap": 0.02,
                    "row": [
                        {"name": "body", "type": "text", "size": 3, "max_lines": 5},
                        {"name": "art", "type": "image", "size": 2, "rgb_support": True},
                    ],
                },
            ],
        },
        {
            "title": "Morning walk",
            "body": "The fjord was quiet at seven. Jumping fish, gulls and a lazy fog "
            "over the water, then sun on the hills by eight o'clock.",
            "art": photo(),
        },
    ),
    # A clock: big time, small date in an inverse strip at the bottom.
    "clock": (
        {
            "column": [
                {
                    "name": "time",
                    "type": "text",
                    "size": 4,
                    "align": "center",
                    "sample": "88:88",
                },
                {
                    "name": "date",
                    "type": "text",
                    "size": 1,
                    "align": "center",
                    "inverse": True,
                    "padding": 0.01,
                    "sample": "Wednesday 30 September",
                },
            ]
        },
        {"time": "12:47", "date": "Monday 5 October"},
    ),
    # Italic text, colour text, shapes and a border.
    "mixed": (
        {
            "padding": 0.02,
            "gap": 0.02,
            "row": [
                {
                    "size": 2,
                    "gap": 0.02,
                    "column": [
                        {
                            "name": "quote",
                            "type": "text",
                            "size": 3,
                            "max_lines": 3,
                            "shrink": True,
                            "font": str(FONTS / "DejaVuSerif-Italic.ttf"),
                            "border": {"pixels": 2},
                            "padding": 0.02,
                        },
                        {
                            "name": "warning",
                            "type": "text",
                            "size": 1,
                            "fill": "red",
                            "rgb_support": True,
                            "align": "right",
                            "sample": "Storm warning Åre",
                        },
                    ],
                },
                {
                    "size": 1,
                    "column": [
                        {"name": "dot", "type": "shape", "shape": "circle", "padding": 0.03},
                        {"name": "bar", "type": "shape", "shape": "rectangle", "fill": "gray"},
                    ],
                },
            ],
        },
        {
            "quote": "jump first, ask questions later: fjords forgive",
            "warning": "Storm warning Åre",
        },
    ),
}
