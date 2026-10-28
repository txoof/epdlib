# epdlib

epdlib is a Python library for drawing layouts (text, images and shapes in sections of the screen) and showing them on e-paper and other frame-buffered displays (displays that show a complete image sent to them from memory). It is used by [PaperPi](https://github.com/txoof/PaperPi).

## Status: version 1 pre-release

Version 1 is a rewrite from scratch. It is published as a pre-release (a test version before the final 1.0.0), so its interface may still change. Install it with:

```bash
pip install "epdlib>=1.0.0a1"             # layouts and the virtual driver only
pip install "epdlib[it8951]>=1.0.0a1"     # with the IT8951 driver (Raspberry Pi)
pip install "epdlib[waveshare]>=1.0.0a1"  # with the Waveshare driver (Raspberry Pi)
```

Without `>=1.0.0a1`, `pip install epdlib` installs the old version 0.6.5.2. Its code and documentation are on the [`v0.6` branch](https://github.com/txoof/epdlib/tree/v0.6), with the last state marked by the tag [`v0.6-final`](https://github.com/txoof/epdlib/tree/v0.6-final). Version 1 does not read or run code written for 0.6.

### What version 1 has
- Layouts and drawing without any display attached, for previews, tests and documentation: see [Writing layouts](https://github.com/txoof/epdlib/blob/main/docs/layouts.md).
- A simple interface for display drivers, with a "virtual" driver that saves images as PNG files.
- The IT8951 driver, for the Waveshare 9.7" screen and the other screens sold with Waveshare's IT8951 board (the controller chip for the larger screens), on Raspberry Pi OS "bookworm" and "trixie": see [IT8951 screens](https://github.com/txoof/epdlib/blob/main/docs/it8951.md).
- The Waveshare driver, for Waveshare's small screens (tested so far: 7.5" V2, 5.83" and 5.65" 7-colour): see [Waveshare screens](https://github.com/txoof/epdlib/blob/main/docs/waveshare.md).
- Time limits on every wait for the display, so a stuck display gives an error instead of freezing the program.

Progress is tracked in [milestones](https://github.com/txoof/epdlib/milestones).

## Development

epdlib supports Python 3.11 (Raspberry Pi OS "bookworm") and newer; development uses 3.13 (Raspberry Pi OS "trixie").

It uses [uv](https://docs.astral.sh/uv/), a tool that installs the right Python version and all the packages epdlib needs into a separate folder (`.venv`), and [ruff](https://docs.astral.sh/ruff/), a tool that checks code style.

```bash
uv sync                    # install everything
uv run pytest              # run the tests (tests that need a real display are skipped)
uv run pytest -m hardware  # run only the tests that need a real display (on the Pi)
uv run ruff check .        # check code style
uv run ruff format .       # fix code formatting
```

See [CLAUDE.md](https://github.com/txoof/epdlib/blob/main/CLAUDE.md) for how work is organized, and [Releasing](https://github.com/txoof/epdlib/blob/main/docs/releasing.md) for how a new version is published.

## License

GPL v3 or later. See [LICENSE](https://github.com/txoof/epdlib/blob/main/LICENSE).
