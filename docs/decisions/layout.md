# Layout engine

Status: proposed (M3, issue #79). Decided with txoof in the terminal on 2026-10-05.

This note records how epdlib v1 describes and draws layouts. How to write a layout is in
[`../layouts.md`](../layouts.md).

## Problem

A layout says which parts of the screen show what: a title here, text there, a picture on
the right. In v0.6 every block had a width and height as a share of the screen, and a
position: either fixed, or "after" another block (`abs_coordinates: (None, 0)` with
`relative: ('l_head', 'r_head')`).

What v0.6 did well, and v1 keeps:
- Layouts "just worked" on any screen size, because sizes were shares of the screen.
- Layouts are plain data, so they can be checked and, later, edited in a web interface.
- Each block is drawn directly in what the screen can show (see PaperPi
  `docs/decisions/display-driver-interface.md`).

What v0.6 did badly:
- The relative-position arithmetic was easy to get wrong.
- Text measuring was unreliable: italic letters were cut off at the left edge (old issue
  14), and it was never clear whether a letter was fully inside the block. The cause: the
  width ignored the left edge of the measured text box, the height was rounded down, and
  the text was measured from one reference point and pasted using another calculation.
- The automatic font size was a guess based on typical letter widths (`chardist`), which
  was slow at start-up and could give text that did not fit.
- The font size could change from one refresh to the next when the text changed.
- A font size set in the layout did not always win (old issue 58).

## Options considered

**Describing positions**
1. Keep v0.6's fixed and relative positions with clearer names. Rejected: the arithmetic
   stays.
2. A grid of named cells, like CSS "grid template areas". Rejected: exact proportions need
   many cells or extra size lists, and deep nesting is hard to draw.
3. Render HTML in a headless browser (InkyPi, TRMNL). Rejected: Chromium needs a few
   hundred MB and seconds to start, too heavy for a Pi 3, and it breaks the
   draw-each-block-in-the-screen's-colours rule.
4. **Rows and columns that nest**, like CSS flexbox, Home Assistant's horizontal and
   vertical stacks, and Qt/Kivy box layouts. **Chosen.** It is the most common method, and
   the arithmetic is about 50 lines, so no library is needed for it.

**Choosing the font size**
1. From the text: the largest size at which this text fits. Rejected: the size changes
   when the text changes, which looks bad.
2. **From the block: worked out once, from the block's height, `max_lines` and an optional
   sample text.** Chosen.

**Writing layouts**
1. TOML, like PaperPi's config. Rejected: TOML hides nesting.
2. **Python dictionaries in a plugin's `layouts.py`, plus JSON files** for a future layout
   editor. Chosen.

## Decision (proposed)

### Rows and columns
- A layout is a `row` or `column` list. Items are blocks, or more rows and columns.
- Each item has a `size`: its share of the free space. Shares need not add up to 1.
- Or it has `pixels`: a fixed size that is taken first (dividers, status strips, icons).
  Never both. If fixed sizes need more than the space, the error names the items.
- Positions are rounded on the running total, so items always fill the space exactly:
  no gaps and no overlaps from rounding.
- Blocks cannot overlap. An "overlay" option (a small block on top of another) can be
  added later if a plugin needs it.

### Spacing
- `padding`: empty space inside a block or container, around its contents.
- `gap`: empty space between the items of a row or column.
- Both are a share of the screen's shorter side (for example `0.02`), so they scale with
  the screen, or `{"pixels": n}` for a fixed amount. The same holds for `border`,
  `font_size` and `line_width`.

### Blocks
- **text**: wraps by words, breaks words that are too long, keeps `\n` line breaks,
  and cuts with "…" (`ellipsis`) after `max_lines` lines. Alignment left, center, right
  and top, center, bottom, or `random` (moves the text a little on each refresh).
- **image**: `fit` is `contain` (whole image, keep its shape), `cover` (fill the block,
  cut the sides), `stretch` or `none`. Aligned like text (old issue 23). Transparent parts
  get the block's background.
- **shape**: `rectangle`, `ellipse`, `hline`, `vline` (a line of `line_width` across the
  middle).
- Every block: `fill`, `background` (colour names or `#rrggbb`), `border`, `inverse`
  (swaps fill and background), `rgb_support`.

### Text size
- **The size comes from the block, not from the text.** It is worked out once, when the
  layout is prepared for a screen:
  1. The largest size at which `max_lines` lines fit the block's height.
  2. If the block has a `sample` (the longest text it normally shows, e.g. `"88:88"` for a
     clock), the size is reduced until the sample fits the width as well. A block with
     fixed `text` (a label) uses that text as its sample.
- A `font_size` in the layout always wins (old issue 58).
- `shrink: true`: when the text does not fit, try 80% and then 60% of the size, and no
  other sizes. A smaller step may use extra lines if they fit the height. The size changes
  only between these three steps.
- Too long at the final size: wrapped, then cut with "…". Text never spills out of its
  block.

### Measuring text
- Every measurement and every drawing call uses the same reference point: the left end of
  the line the text sits on (the baseline; Pillow anchor `ls`).
- Line height is the font's ascent plus descent: the same for every line, so a line with
  a *g* does not move the others.
- Line width is the real ink, including letters that reach left of the start (italic *f*,
  *j*) or past the end. Text is moved right by any left overhang.
- An image test draws italics, *gjpqy* and accents (*Å*) in every alignment and size, and
  checks that no ink is outside the block.
- Speed: nothing is measured when a layout is loaded. Words are measured once and added
  up; each finished line is checked once. Wrapping stops one line past `max_lines`.
  Fonts are loaded once and kept. A speed test fails if a text block on a 9.7" screen
  takes more than 50 ms on a Pi 4 (150 ms with `shrink`, which can try three sizes).

### Colour and gray
- Each block is drawn in gray (or colour, on colour screens with `rgb_support: true`),
  then reduced to what the screen shows: 1-bit, a number of gray levels, a palette (such
  as the 7-colour screens), or full colour.
- **Text is never dithered**: each pixel goes to the nearest available shade, so it stays
  sharp. **Images and shapes are dithered**, so a gray fill shows as a dot pattern on a
  black-and-white screen instead of disappearing.
- Without `rgb_support`, a block on a colour screen is drawn in black and white.
- `ScreenMode.convert()` turns any finished image (for example one a program drew itself)
  into the screen's mode as a last step.

### Fonts
- The default font is DejaVu Sans, shipped with epdlib (free licence, covers most
  European scripts). Pillow's built-in font has no letters such as *Å*.
- epdlib always uses Pillow's basic text layout. Pillow would otherwise switch to its
  "raqm" layout on computers that have the libraqm library installed. That layout places
  letters at fractional positions, so the same text measured and wrapped differently on
  this Pi (no libraqm) and on GitHub's test machines (libraqm installed). With the basic
  layout, a layout looks the same on every computer, and the image tests compare pixel by
  pixel. The cost: scripts that need letter shaping (such as Arabic or Devanagari) are not
  drawn correctly. That can be added later as an option.

### Layout files and safety
- A plugin's `layouts.py` is Python code, so loading it runs it. It has the same trust as
  the plugin itself: install plugins only from sources you trust.
- JSON layouts are data only. They are read with Python's `json` module, never with
  `eval` or `pickle`. Limits: font and image paths must be inside the allowed folders
  (paths with `..` that climb out are refused), at most 10 levels of nesting, at most
  1 MB per file, and fixed sizes of at most 20,000 pixels.

### Driver interface and the virtual driver
- `epdlib.drivers.Driver` defines `init`, `write(image, fast)`, `clear`, `sleep` and
  `close`, a `timeout` in seconds, `DisplayTimeout` and `DisplayError`, and the
  `DisplayInfo` description (model, size, mode, fast refresh, tested). Use a driver in a
  `with` block so `close` always runs.
- `VirtualDriver` writes numbered PNG files and `latest.png`, and can pretend to be any
  screen size and mode. It is used for tests and previews.
- Importing epdlib, its drivers package or the virtual driver never imports `spidev`,
  `gpiod` or other pin libraries; a test checks this.
- The helper process for screen writes, and the IT8951 and Waveshare drivers, come in
  later M3 work.

## Later
- A "size group", so several blocks share one font size.
- Overlay blocks.
- 4-gray mode for small Waveshare screens (old issues 71, 166).
- A gallery of example layouts in the docs, rendered by CI (`tests/examples.py` is a
  start).
