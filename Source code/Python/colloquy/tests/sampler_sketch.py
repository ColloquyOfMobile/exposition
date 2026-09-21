# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/sampler_sketch.py

"""What `microphone_sampler` is, read out of `microphone_sampler`.

The same arrangement as `drivers/arduino/firmware.py` and
`test_microphone_signal/plotter_sketch.py`, and for the same reason: the
version this repo would flash and the version on the board have to agree,
and **nothing says so when they do not**. A board on firmware 1 asked for
two channels does not go quiet - it answers `error commands: b | ?`,
which is a perfectly good reply to a question it has never had, and which
cost a real hour being read as a missing lead.

Two tests share this board and they need different things of it:

- **`test goertzel ear`** asks for `b`, which is untouched to the last
  byte since firmware 1. Any sampler firmware will do.
- **`scope`** asks for `d`, which arrived in firmware 2 along with the
  second channel. Below that it gets a refusal.

So `verdict()` takes the minimum as an argument rather than knowing one.
A version that is old *enough* for the test in hand is not a fault, and
reporting one as a fault teaches people to ignore the reading.

`MIC_PIN` is a token (`A0`) rather than a number, which is why this
cannot simply borrow `firmware._sketch_define`, and which is also the
point: a sketch edited to sample `A5` plots a pin nobody wired, and the
page should say which pin *this* sketch reads rather than restate the one
the bench happens to use today.
"""
import re
from functools import lru_cache
from pathlib import Path

# colloquy/tests/ -> colloquy/ -> Python/ -> Source code/, exactly as
# firmware.SKETCH_PATH walks out to the installation's own sketch.
SKETCH_FOLDER = Path(__file__).resolve().parents[3] / "Arduino" / "microphone_sampler"
SKETCH_PATH = SKETCH_FOLDER / "microphone_sampler.ino"

# What the board prefixes its greeting - and its status line - with. The
# one thing that says the sketch on the other end is this sketch and not
# some other one left on the board.
GREETING_PREFIX = "microphone_sampler"


@lru_cache(maxsize=None)
def _define(name):
    """One `#define NAME <token>` out of the sketch, as written.

    Deliberately not int(): two of the four worth reading here are `A0`
    and `A1`, and a number is the one thing neither of them is.
    """
    text = SKETCH_PATH.read_text(encoding="utf-8")
    match = re.search(rf"^#define\s+{name}\s+(\S+)", text, re.MULTILINE)
    if match is None:
        raise RuntimeError(f"No #define {name} in {SKETCH_PATH}")
    return match.group(1)


def firmware_version():
    """The protocol version the sketch in this repo implements."""
    return int(_define("FIRMWARE_VERSION"))


def baudrate():
    """The rate the sketch sets its serial port to."""
    return int(_define("BAUDRATE"))


def mic_pins():
    """The two ADC pins it samples - `('A0', 'A1')` as it ships.

    Both, because the second is the whole of what firmware 2 added and
    the whole of what `scope` is for: a channel nobody wired reads its
    neighbour rather than silence.
    """
    return _define("MIC_PIN"), _define("MIC_PIN_B")


def describe():
    """One line for the page: what would be on the board if flashed now."""
    first, second = mic_pins()
    return (
        f"firmware {firmware_version()}, {first} and {second}, "
        f"at {baudrate()} baud"
    )


def firmware_in(line):
    """The firmware version in a greeting or a status line, or None.

    The greeting is the one place the board says what it is, and it says
    it unprompted on every reboot - which is every time the port opens,
    since opening toggles DTR. So it costs nothing and is known before
    the first capture is asked for.
    """
    if not line:
        return None
    for piece in line.split():
        name, _, value = piece.partition("=")
        if name == "firmware":
            try:
                return int(value)
            except ValueError:
                return None
    return None


def verdict(found, minimum, needs=None):
    """Is the board on the other end one this test can use? In words.

    `found` is what the greeting said, or None if nothing has been heard.
    `minimum` is what the asking test needs - see the module docstring on
    why that is an argument - and `needs` names what it needs it *for*,
    because "the second channel needs 2" tells somebody what they lose
    and "this needs at least 2" does not.

    Four answers rather than two, because "not the version in this repo"
    and "too old to work" are different facts and only one of them is a
    reason to go and find a USB lead. Never heard from is a fifth, and it
    is deliberately not phrased as a fault: nothing has been asked yet.
    """
    here = firmware_version()

    if found is None:
        return "not known yet - press 'ask the board', or start a run"
    if found < minimum:
        wants = f"{needs} needs" if needs else "this needs at least"
        return (
            f"firmware {found} - too old, {wants} {minimum}. "
            f"Flash it: the sketch here is firmware {here}"
        )
    if found < here:
        return (
            f"firmware {found} - older than the sketch here ({here}), and "
            f"new enough for this test, which needs {minimum}"
        )
    if found > here:
        return (
            f"firmware {found} - newer than the sketch here ({here}). "
            "Something else flashed this board, or this checkout is behind"
        )
    # Said in the affirmative rather than left as a bare version, and
    # `needs` is what makes it worth reading: "it knows both channels" is
    # the thing being asked about, where "firmware 2" is a number the
    # reader has to know the significance of.
    has = f", and it knows {needs}" if needs else ""
    return f"firmware {found} - the sketch in this repo{has}"


def is_usable(found, minimum):
    """Would this test work against the board that greeted? True/False.

    Split from `verdict` so a refusal can be decided on without matching
    on the prose of a sentence somebody may reword.
    """
    return found is not None and found >= minimum
