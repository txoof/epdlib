# epdlib

> **Looking for the current release?** epdlib 0.6 is installed with `pip install epdlib` (version 0.6.5.2 on [PyPI](https://pypi.org/project/epdlib/)). Its code and documentation are on the [`v0.6` branch](https://github.com/txoof/epdlib/tree/v0.6). The last state is marked with the tag [`v0.6-final`](https://github.com/txoof/epdlib/tree/v0.6-final).

epdlib is a Python library for drawing layouts (text, images and shapes in sections of the screen) and showing them on e-paper and other frame-buffered displays (displays that show a complete image sent to them from memory). It is used by [PaperPi](https://github.com/txoof/PaperPi).

## Status: version 1 is being rewritten

This branch (`main`) holds epdlib **version 1**, which is being written from scratch. It is not usable yet. Do not install from this branch; `pip install epdlib` gives the working version 0.6.

### What version 1 will add
- Drawing layouts to an image without any display attached, for previews, tests and documentation
- A simple interface for display drivers, with a "virtual" driver that saves images to files
- Support for displays that use the IT8951 controller chip (such as the Waveshare 9.7") on Raspberry Pi OS "trixie"
- Time limits on every wait for the display, so a stuck display gives an error instead of freezing the program
- Tests and generated documentation with example images

### What works so far
- Layouts and drawing without a display: see [Writing layouts](docs/layouts.md).
- The virtual driver, which saves images as PNG files.

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

See [CLAUDE.md](CLAUDE.md) for how work is organized.

## License

GPL v3 or later. See [LICENSE](LICENSE).
