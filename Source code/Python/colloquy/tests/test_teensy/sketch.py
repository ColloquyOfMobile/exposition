# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_teensy/sketch.py

"""What `teensy_check` is, read out of `teensy_check.ino`, and what its
replies say. No node, no port.

The same arrangement as `sampler_sketch.py`: the version this repo would
flash is read from the sketch rather than restated, so the two cannot
drift without the page saying so.
"""
import re
from functools import lru_cache
from pathlib import Path

# colloquy/tests/test_teensy/ -> ... -> Source code/
SKETCH_FOLDER = Path(__file__).resolve().parents[4] / "Arduino" / "teensy_check"
SKETCH_PATH = SKETCH_FOLDER / "teensy_check.ino"

# arduino-cli's name for the board, from PJRC's Teensyduino core.
FQBN = "teensy:avr:teensy41"

# What every status line starts with: the sketch naming itself.
STATUS_PREFIX = "teensy_check"


@lru_cache(maxsize=None)
def _define(name):
    """One `#define NAME <token>` out of the sketch, as written."""
    text = SKETCH_PATH.read_text(encoding="utf-8")
    match = re.search(rf"^#define\s+{name}\s+(\S+)", text, re.MULTILINE)
    if match is None:
        raise RuntimeError(f"No #define {name} in {SKETCH_PATH}")
    return match.group(1)


def firmware_version():
    return int(_define("FIRMWARE_VERSION"))


def board_name():
    return _define("BOARD_NAME").strip('"')


def blink_fast_seconds():
    """How long `b` makes the LED flicker for."""
    return int(_define("BLINK_FAST_MS")) / 1000


def _seconds(name):
    return int(_define(name)) / 1000


def tone_step_seconds():
    """How long `l` lights each TONE LED alone."""
    return _seconds("TONE_STEP_MS")


def tone_all_seconds():
    """How long `l` then lights all five together."""
    return _seconds("TONE_ALL_MS")


def tone_hold_seconds():
    """How long `l <n>` keeps one TONE LED lit."""
    return _seconds("TONE_HOLD_MS")


@lru_cache(maxsize=None)
def tone_pins():
    """The Teensy pin of each voice slot, slot 1 first, as the sketch
    drives them (`TONE_PINS[] = {...}`)."""
    text = SKETCH_PATH.read_text(encoding="utf-8")
    match = re.search(r"TONE_PINS\[\]\s*=\s*\{([^}]*)\}", text)
    if match is None:
        raise RuntimeError(f"No TONE_PINS[] in {SKETCH_PATH}")
    return tuple(int(pin) for pin in match.group(1).split(","))


def chase_seconds():
    """How long a whole `l` lasts: each slot alone, then all together."""
    return tone_step_seconds() * len(tone_pins()) + tone_all_seconds()


def describe():
    """One line for the page: what would be on the board if flashed now."""
    return f"teensy_check firmware {firmware_version()} for a Teensy 4.1"


def parse_status(line):
    """A `?` reply -> its fields as a dict of strings, or None.

    None for anything that is not this sketch's status line - which is
    the finding, not an error: another sketch, or nothing, is on the board.
    """
    if not line or not line.startswith(STATUS_PREFIX + " "):
        return None
    fields = {}
    for piece in line.split()[1:]:
        name, sep, value = piece.partition("=")
        if sep:
            fields[name] = value
    return fields


def number(fields, name):
    """One numeric field out of `parse_status`'s dict, or None."""
    try:
        return float(fields[name])
    except (KeyError, TypeError, ValueError):
        return None
