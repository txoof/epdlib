import subprocess
import sys

HARDWARE = ["spidev", "gpiod", "RPi", "gpiozero", "lgpio"]


def test_import_does_not_load_hardware_libraries():
    """Importing the layout code and the virtual driver never imports pin or SPI libraries."""
    code = (
        "import sys, epdlib, epdlib.drivers, epdlib.drivers.virtual\n"
        f"print([m for m in {HARDWARE!r} if m in sys.modules])"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"
