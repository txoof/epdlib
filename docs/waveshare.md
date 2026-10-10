# Waveshare screens

The Waveshare driver shows images on Waveshare's small e-paper screens: the ones connected through Waveshare's e-Paper HAT (the board between the Raspberry Pi and the screen), without the IT8951 controller. For screens with the IT8951 controller, see [IT8951 screens](it8951.md).

| Model (`model=`) | Size in pixels | Colours | Status |
|---|---|---|---|
| `"epd7in5_V2"` (the default) | 800 × 480 | black and white | tested |

Models are named by Waveshare's file for them, which is also the name used in Waveshare's wiki. "Tested" means the driver was run on that screen: start, full and fast writes (also checked by eye), clear, sleep, time limits and releasing the pins. "Untested" means it should work but has not been run on a real screen. Reports are welcome. More models will follow.

## How the driver uses Waveshare's code

Waveshare writes a Python file for each screen model, with the screen's start-up commands and how it expects images. epdlib uses these files **unchanged**, copied from [Waveshare's repository](https://github.com/waveshareteam/e-Paper) into `src/epdlib/drivers/waveshare/vendor/`. `vendor/UPSTREAM.txt` says which version they are, and a test checks that they still match it, so they are never edited.

Only Waveshare's shared helper file, `epdconfig.py`, is replaced by epdlib's own. Every model file uses it for each pin change, each SPI write (SPI is the wired data connection to the HAT) and each wait. Waveshare's version uses the `gpiozero` library, which has had problems on new kernels (the kernel is the core of the operating system) and on the Pi 5, and it waits for the screen's busy pin forever. epdlib's version:

- uses `gpiod` and `spidev`,
- stops every wait for the busy pin when the operation's time limit runs out (`DisplayTimeout`); the fixed pauses in Waveshare's files still run in full,
- claims only the pins below, and always releases them in `close()`,
- pauses 1 ms between reads of the busy pin, so a wait does not keep a processor core busy.

A model whose Waveshare file does not work is not repaired in epdlib. It is removed from the table of models, listed as not working on this page, and reported to Waveshare.

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

The user running the program must be in the `gpio` and `spi` groups. On Raspberry Pi OS the first user already is; for another user: `sudo usermod -aG gpio,spi <user>`, then log in again.

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

`sleep()` puts the screen into deep sleep and switches its power off, as Waveshare recommends after every write: a screen left powered for a long time can be damaged. `sleep()` takes a little over 2 s, because Waveshare's file pauses 2 s after the sleep command. The next `write()` or `clear()` wakes the screen, which runs its start-up again (a reset and power-on, at least 0.2 s). Calling `sleep()` again while the screen sleeps does nothing.

After an error in `write()`, `clear()` or `sleep()`, the next `write()` or `clear()` also runs the start-up first, because the screen may be left half-way. `init()` can be called at any time: it closes and starts the screen fresh.

Only one Waveshare screen can be open at a time in one program, because Waveshare's files share one helper file.

## Settings

**`model`** (default `"epd7in5_V2"`): which screen, from the table above. The screen does not report its model, so the driver cannot check it: a wrong model gives a garbled or blank image.

**`power_pin`** (default `18`): GPIO 18 switches the screen's power on newer Waveshare HATs, so the driver claims it. Other numbers raise `ValueError`. Use `power_pin=None` to leave GPIO 18 alone, for example on a Pi with a HiFiBerry sound card, which also needs GPIO 18. On a HAT with a PWR pin, the screen may then get no power.

**`max_refresh`** (default 4): after this many fast writes in a row, the next write is a full one. Fast writes refresh the whole screen too, but more briefly, so faint traces of earlier images (ghosting) can build up. A normal full write removes most of them. 4 is the recommended value. Higher numbers flash less often but leave more leftovers; 0 means never force a full write: then call `clear()` or a full `write()` yourself now and then, for example once an hour. Ignored on screens without fast writes.

**`timeout`** (default 30 s): the longest one operation (`init`, `write`, `clear`, `sleep`) may take. When it runs out, the driver raises `DisplayTimeout`. It never waits forever.

## Refresh types

Measured on the 7.5" V2 with a Pi 3:

| Call | What the screen does |
|---|---|
| `write(image)` | Full refresh of the whole screen, with flashes (about 7 s). |
| `write(image, fast=True)` | Waveshare's fast full refresh: the whole screen, with fewer and shorter flashes (about 3.7 s). If the image has the same pixels as the one on the screen, nothing is sent, and it does not count toward `max_refresh`. |
| `clear()` | Full refresh to white (about 7 s). |

The first write after `init()` and the first write after an error are always full, because the driver then does not know what the screen shows. After `sleep()` the driver still knows the last image, so a fast write after sleep is still fast. A fast write after `clear()` is fast too. A full write or `clear()` starts the count for `max_refresh` again.

Waveshare's file also has a partial refresh for the 7.5" V2. Checked by eye, it flashed the whole screen as well and took the same time as the fast full refresh (about 3.7 s), but it depends on the screen's controller remembering the last image, so the driver uses the fast full refresh.

Switching between full and fast writes runs the screen's start-up for that mode again (about 0.2 s, on top of the times above).

## Errors

| Error | Meaning |
|---|---|
| `ValueError` when making the driver | A setting is wrong, for example an unknown model. The message says which. |
| `DisplayError: /dev/spidev0.0 is missing` | SPI is off: see [Install](#install). |
| `DisplayError: no permission to use ...` | The user is not in the `gpio` and `spi` groups: see [Pins](#pins). |
| `DisplayError: /dev/gpiochip0 has no ...` | This does not look like a Raspberry Pi. |
| `DisplayError: cannot claim GPIO17, ...` | Another program is using these pins. Stop it first. On a Pi with a HiFiBerry, use `power_pin=None`. |
| `DisplayError: another Waveshare screen is open` | Close the other driver first. |
| `DisplayError: image is ...` | The image is not the screen's size. |
| `DisplayError: screen is closed` | `write` or `clear` before `init()` or after `close()`: call `init()` first. |
| `DisplayTimeout` | The screen did not finish in time: check the cable and the model. The next `write()` or `clear()` starts the screen again. |

## Hardware test

With the screen attached:

```bash
uv run pytest -m hardware tests/test_waveshare_hardware.py
```

For another screen, set `EPDLIB_WAVESHARE_MODEL` to its name from the table at the top. Set `EPDLIB_WAVESHARE_NO_POWER_PIN=1` to leave GPIO 18 alone. The test draws a test page, does fast writes (including one right after sleep), wakes the screen from sleep, starts it again after `close()`, and checks that each step finishes within its time limit. It ends with a clear.
