# Waveshare screens

The Waveshare driver shows images on Waveshare's small e-paper screens: the ones connected through Waveshare's e-Paper HAT (the board between the Raspberry Pi and the screen), without the IT8951 controller. For screens with the IT8951 controller, see [IT8951 screens](it8951.md).

| Model (`model=`) | Size in pixels | Colours | Status |
|---|---|---|---|
| `"epd7in5_V2"` (the default) | 800 × 480 | black and white | untested |

Models are named by Waveshare's file for them, which is also the name used in Waveshare's wiki. "Tested" means the driver was run on that screen: start, writes, clear, sleep, time limits and releasing the pins. "Untested" means it should work but has not been run on a real screen. Reports are welcome. More models will follow.

## How the driver uses Waveshare's code

Waveshare writes a Python file for each screen model, with the screen's start-up commands and how it expects images. epdlib uses these files **unchanged**, copied from [Waveshare's repository](https://github.com/waveshareteam/e-Paper) into `src/epdlib/drivers/waveshare/vendor/`. `vendor/UPSTREAM.txt` says which version they are, and a test checks that they still match it, so they are never edited.

Only Waveshare's shared helper file, `epdconfig.py`, is replaced by epdlib's own. Every model file uses it for each pin change, SPI write and wait. Waveshare's version uses the `gpiozero` library, which is unreliable on new kernels and does not work on the Pi 5, and it waits for the screen's busy pin forever. epdlib's version:

- uses `gpiod` and `spidev`,
- stops every wait when the operation's time limit runs out (`DisplayTimeout`),
- claims only the pins below, and always releases them in `close()`,
- pauses 1 ms between reads of the busy pin, so a wait does not keep a processor core busy.

A model whose Waveshare file does not work is not repaired in epdlib. It is marked as not working and reported to Waveshare.

## Install

Install as for [IT8951 screens](it8951.md#install) (turn SPI on, install `gcc` and `python3-dev`, make a virtual environment), but with the `waveshare` install group:

```bash
~/epdlib-venv/bin/pip install "epdlib[waveshare] @ git+https://github.com/txoof/epdlib"
```

For working on epdlib itself: `uv sync --extra waveshare`.

## Pins

The driver uses Waveshare's standard pins, so a HAT plugged onto the 40-pin header works as it is. These are GPIO numbers, not pin positions on the header.

| Pin | GPIO | Use |
|---|---|---|
| RST | 17 | reset |
| DC | 25 | says whether an SPI write is a command or data |
| BUSY | 24 | the screen says it is still working |
| PWR | 18 | switches the screen's power on newer HATs; see `power_pin` |
| CS | 8 | chip select (the pin that tells the screen "this transfer is for you"); used by the kernel's SPI driver, not claimed by epdlib |

SPI bus 0, device 0 (`/dev/spidev0.0`), at 4 MHz. Other pins are not supported yet.

## Use

```python
from PIL import Image
from epdlib.drivers.waveshare import WaveshareDriver

image = Image.open("picture.png").resize((800, 480))  # must be the screen's size

with WaveshareDriver("epd7in5_V2") as screen:
    screen.write(image)
    screen.sleep()
```

The image is reduced to what the screen can show (for the 7.5" V2: black and white, with dot patterns for grays). The `with` block starts the screen (`init`) and always releases the pins and SPI at the end, even after an error.

`sleep()` puts the screen into deep sleep and switches its power off, as Waveshare recommends after every write: a screen left powered for a long time can be damaged. The next `write()` or `clear()` wakes it, which runs the screen's start-up again (a reset, about 0.2 s). Calling `sleep()` again while the screen sleeps does nothing. Call `init()` again only after `close()`.

Only one Waveshare screen can be open at a time in one program, because Waveshare's files share one helper file.

## Settings

**`model`** (default `"epd7in5_V2"`): which screen, from the table above. The screen does not report its model, so the driver cannot check it: a wrong model gives a garbled or blank image.

**`power_pin`** (default `18`): GPIO 18 switches the screen's power on newer Waveshare HATs, so the driver claims it. Use `power_pin=None` to leave GPIO 18 alone, for example on a Pi with a HiFiBerry sound card, which also needs GPIO 18. On a HAT with a PWR pin, the screen may then get no power.

**`timeout`** (default 30 s): the longest one operation (`init`, `write`, `clear`, `sleep`) may take. When it runs out, the driver raises `DisplayTimeout`. It never waits forever.

## Refresh types

| Call | What the screen does |
|---|---|
| `write(image)` | Full refresh of the whole screen, with flashes. |
| `write(image, fast=True)` | The same as a full refresh for now. Fast writes on the 7.5" V2 will follow. |
| `clear()` | Full refresh to white. |

## Errors

| Error | Meaning |
|---|---|
| `ValueError` when making the driver | A setting is wrong, for example an unknown model. The message says which. |
| `DisplayError: /dev/spidev0.0 is missing` | SPI is off: see Install, step 1. |
| `DisplayError: cannot claim GPIO17, ...` | Another program is using these pins. Stop it first. On a Pi with a HiFiBerry, use `power_pin=None`. |
| `DisplayError: another Waveshare screen is open` | Close the other driver first. |
| `DisplayError: image is ...` | The image is not the screen's size. |
| `DisplayError: screen is closed` | `write` or `clear` before `init()` or after `close()`: call `init()` first. |
| `DisplayTimeout` | The screen did not finish in time: check the cable and the model. Call `init()` again to reset it. |

## Hardware test

With the screen attached:

```bash
uv run pytest -m hardware tests/test_waveshare_hardware.py
```

For another screen, set `EPDLIB_WAVESHARE_MODEL`, for example `EPDLIB_WAVESHARE_MODEL=epd7in5_V2`. Set `EPDLIB_WAVESHARE_NO_POWER_PIN=1` to leave GPIO 18 alone. The test draws a test page, wakes the screen from sleep, starts it again after `close()`, and checks that each step finishes within its time limit. It ends with a clear.
