# Writing layouts

A layout says which part of the screen shows what. It is plain data: dictionaries and
lists. The reasons behind the design are in
[`decisions/layout.md`](decisions/layout.md).

## A first layout

```python
from epdlib import Layout, ScreenMode
from epdlib.drivers.virtual import VirtualDriver

layout = Layout(
    {
        "column": [
            {"name": "title", "type": "text", "size": 1},
            {
                "size": 4,
                "row": [
                    {"name": "body", "type": "text", "size": 3, "max_lines": 4},
                    {"name": "art", "type": "image", "size": 2},
                ],
            },
        ]
    }
)

page = layout.prepare(800, 480, ScreenMode.gray(16))  # once per screen
image = page.render({"title": "Hello", "body": "Some text", "art": "cat.png"})

with VirtualDriver(800, 480, ScreenMode.gray(16), "out") as display:
    display.write(image)  # saves out/latest.png
```

```
+---------------------------+
|           title           |   1 part of the height
+----------------+----------+
|      body      |   art    |   4 parts of the height
+----------------+----------+
     3 parts        2 parts of the width
```

## Rows, columns and sizes

- `{"row": [...]}` puts items side by side; `{"column": [...]}` puts them on top of each
  other. Items are blocks or more rows and columns, up to 10 levels deep.
- `size` is an item's share of the free space (default 1). `{"size": 1}` and
  `{"size": 3}` split the space 1:3. Shares need not add up to 1.
- `pixels` gives an item a fixed size, taken before the shares: `{"pixels": 2}` for a
  thin divider. An item has `size` or `pixels`, not both.

## Spacing and lengths

`padding` (inside a block or container), `gap` (between items, set on the row or column),
`border`, `font_size` and `line_width` are lengths. A length is either:
- a number from 0 to 1: a share of the screen's **shorter side**, so `0.02` is 2% and
  scales with the screen, or
- `{"pixels": n}`: a fixed number of pixels.

## Block types

Every block has a unique `name` and a `type`. Options for all blocks:

| Option | Default | Meaning |
|---|---|---|
| `fill` | `"black"` | colour of text and shapes: a name such as `"red"` or `"#rrggbb"` |
| `background` | `"white"` | colour behind the content |
| `border` | none | a line around the block's edge (a length) |
| `inverse` | `false` | swap `fill` and `background` |
| `padding` | none | space inside the block (a length) |
| `rgb_support` | `false` | use colour on colour screens; otherwise black, white and gray |

### text

| Option | Default | Meaning |
|---|---|---|
| `text` | `""` | text shown when `render` gets no value for this block (for labels) |
| `max_lines` | 1 | how many lines the block is sized for |
| `sample` | none | the longest text the block normally shows, used to choose the size |
| `font_size` | automatic | a fixed size (a length); always wins |
| `shrink` | `false` | allow 80% and 60% of the size when the text does not fit |
| `font` | DejaVu Sans | path to a `.ttf` or `.otf` font file |
| `align` | `"left"` | `left`, `center`, `right` or `random` |
| `valign` | `"center"` | `top`, `center`, `bottom` or `random` |
| `ellipsis` | `"…"` | added where too-long text is cut |

### image

`render` takes a Pillow image or a file path. `image` in the layout sets a default path.

| Option | Default | Meaning |
|---|---|---|
| `fit` | `"contain"` | `contain`: whole image, shape kept. `cover`: fills the block, sides cut. `stretch`: fills the block, shape changed. `none`: original size |
| `align` / `valign` | `"center"` | which side the image sits on, and which side is kept when it is cut |

### shape

`shape` is `rectangle` (default), `ellipse`, `hline` or `vline`. Lines are `line_width`
thick (default 1 pixel) and drawn across the middle of the block. `render` can take
`{"fill": "red", "background": "black"}` to change colours while running.

## How the text size is chosen

The font size depends on the **block**, never on the text it shows, so it stays the same
from one refresh to the next. It is worked out once, by `layout.prepare()`:

1. **Height:** the largest size at which `max_lines` lines fit the block's height (inside
   its padding and border). The height of a line is the font's full height, from the top
   of the tallest letters to the bottom of letters such as *g* and *y*.
2. **Width, with a sample:** if the block has a `sample`, the size is made smaller until
   the sample fits the block's width in `max_lines` lines. Use the longest text the block
   normally shows: `"88:88"` for a clock, `"Wednesday 30 September"` for a date. A block
   with fixed `text` (a label) uses that text as its sample.
3. **Fixed:** `font_size` replaces both steps.

Without a sample, a one-line block in a wide, low space can get a font that is too large
for its text. Add a `sample`, or `shrink: true`.

### Text that does not fit

1. Words are moved to the next line. A word longer than a whole line is broken between
   letters. `\n` in the text always starts a new line.
2. With `shrink: true`, if the text still does not fit, it is tried at 80% and then 60% of
   the size. A smaller size may use extra lines when they fit the block's height.
3. Whatever does not fit after the last line is cut, and the last line ends with "…".

Text never spills out of its block, and letters that lean (italics) or hang below the line
are never cut off.

## Colour and gray

`ScreenMode` says what the screen can show:

| Mode | Screens |
|---|---|
| `ScreenMode.bw()` | black and white |
| `ScreenMode.gray(16)` | 16 shades of gray, e.g. the 9.7" IT8951 |
| `ScreenMode.palette()` | the 7-colour screens (or pass your own colours) |
| `ScreenMode.rgb()` | full colour |

Each block is drawn directly in the screen's mode. Text is never dithered, so it stays
sharp; images and shapes are dithered (dot patterns for in-between shades).

## Layouts from JSON files

```python
layout = Layout.from_json("layout.json", asset_dirs=["/usr/share/my-fonts"])
```

A JSON layout has the same shape as the dictionary. Because JSON files may come from other
people, fonts and images must be inside `asset_dirs`, and files over 1 MB are refused.

## Errors

A mistake in a layout raises `LayoutError` with the block's name and the problem, for
example `block 'body': unknown key 'colour' (did you mean 'fill'?)`.
