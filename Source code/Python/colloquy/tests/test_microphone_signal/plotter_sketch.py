# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_microphone_signal/plotter_sketch.py

"""What the plotter sketch samples, read out of the plotter sketch.

The same arrangement as `drivers/arduino/firmware.py`, and for the same
reason: the pin the clip is on and the pin the sketch reads have to be
the same pin, and **nothing says so when they are not**. A sketch left on
`A5` from the photosensor route, with the microphone now on `A0`, plots a
floating pin - which section 6 of the document lists as a failure shape
in its own right. So the page says which pin *this* sketch will read
rather than restating the one the wiring happens to use today.

`MIC_PIN` is a token (`A0`) and not a number, which is why this cannot
simply borrow `firmware._sketch_define`. `MODE` is a token too, and it
matters as much as the pin: envelope and wave draw different things, and
somebody reading "flat" off a wave-mode plot is reading it wrong.
"""
import re
from functools import lru_cache
from pathlib import Path

# colloquy/tests/test_microphone_signal/ -> ... -> Source code/, exactly
# as firmware.SKETCH_PATH walks out to the other sketch.
SKETCH_PATH = (
    Path(__file__).resolve().parents[4]
    / "Arduino"
    / "microphone_plotter"
    / "microphone_plotter.ino"
)


@lru_cache(maxsize=None)
def _define(name):
    """One `#define NAME <token>` out of the sketch, as written.

    Deliberately not int(): the two worth reading here are `A0` and
    `ENVELOPE`, and a number is the one thing neither of them is.
    """
    text = SKETCH_PATH.read_text(encoding="utf-8")
    match = re.search(rf"^#define\s+{name}\s+(\S+)\s*$", text, re.MULTILINE)
    if match is None:
        raise RuntimeError(f"No #define {name} in {SKETCH_PATH}")
    return match.group(1)


def mic_pin():
    """The ADC pin the sketch samples - `A0` as it ships."""
    return _define("MIC_PIN")


def plot_baudrate():
    """The rate to set the Serial Plotter's corner to.

    Not the installation's 1 Mbaud, and a window full of rubbish is
    always these two numbers disagreeing - which is worth being able to
    read off the page while looking at the rubbish.
    """
    return int(_define("PLOT_BAUDRATE"))


def mode():
    """`ENVELOPE` or `WAVE`."""
    return _define("MODE")


def describe():
    """One line for the page: what the sketch would do if flashed now."""
    return f"reads {mic_pin()} in {mode().lower()} mode at {plot_baudrate()} baud"
