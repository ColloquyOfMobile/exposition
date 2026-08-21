# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/arduino/firmware.py

"""What is running on the Arduino, and whether this driver can talk to it.

Two things have to agree between this repo's Python and whatever is
actually flashed on the board, and neither of them says so when it is
wrong:

- **the baud rate**, which lives in `params.json` on this side and in a
  `#define` in the sketch on that side. Open the port at the wrong one and
  the board still answers - with rubbish, byte for byte, for as long as
  you care to watch.
- **the protocol version**, which changes whenever a path is renamed or a
  reply changes shape. An older sketch answers a path it does not know
  with an empty line, so the only symptom is a female who never sees a
  pattern, forty minutes into a test that was supposed to prove the
  decoding works.

The sketch is the source of truth for both, and this reads them out of it:
`sketch_baudrate()` and `sketch_firmware_version()` pull the `#define`s
out of the .ino, the same trick `VirtualSerialPort` already uses to learn
which paths exist. So the numbers are written once, in the file that gets
flashed, and everything else is checked against them.

`parse_greeting()` reads what the board itself says on reboot, and
`problems()` puts the three side by side: what this repo would flash, what
params.json is about to open the port at, and what the board on the other
end says it is.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

# Where the firmware lives, relative to this file rather than to the
# working directory: colloquy/hardware/arduino/ -> ... -> Source code/.
# VirtualSerialPort reads the same file for the list of paths, and imports
# this name rather than working it out a second time.
SKETCH_PATH = (
    Path(__file__).resolve().parents[4]
    / "Arduino"
    / "colloquy_of_mobiles"
    / "colloquy_of_mobiles.ino"
)

# The oldest firmware this driver will still speak to. Written by hand
# rather than read from the sketch, because it answers a different
# question: the sketch says what you would flash today, this says what the
# driver can still cope with. They are the same number only until the
# driver learns to handle two shapes of reply at once.
MINIMUM_FIRMWARE_VERSION = 2

# What v1 was: a bare "Hello!" and no way to ask it anything about itself.
# Kept here so a board that predates the greeting is *diagnosed* rather
# than reported as silent - "firmware 1, flash it" is a far better thing
# to read at a rig than "no response".
LEGACY_GREETING = {"hello": "colloquy of mobiles", "firmware": 1, "baudrate": 57600}
LEGACY_HELLO = b"Hello!"

# Every rate the sketch has ever run at, plus the ones a stray sketch is
# likely to have been left on, fastest first. Only used when the board has
# gone silent: reopening at each in turn is what turns "no response" into
# "it is talking at 57600, so it has the old firmware on it".
PROBE_BAUDRATES = (1000000, 500000, 250000, 115200, 57600, 9600)


@lru_cache(maxsize=None)
def _sketch_define(name):
    """One `#define NAME <number>` out of the sketch, as an int.

    Trailing type suffixes are allowed for (`1000000UL`) - Serial.begin()
    takes an unsigned long, and the sketch says so.
    """
    text = SKETCH_PATH.read_text(encoding="utf-8")
    match = re.search(rf"^#define\s+{name}\s+(\d+)[uUlL]*\s*$", text, re.MULTILINE)
    if match is None:
        raise RuntimeError(f"No #define {name} in {SKETCH_PATH}")
    return int(match.group(1))


def sketch_baudrate():
    """The rate the sketch in this repo sets up its serial port at."""
    return _sketch_define("SERIAL_BAUDRATE")


def sketch_firmware_version():
    """The protocol version the sketch in this repo implements."""
    return _sketch_define("FIRMWARE_VERSION")


def sketch_greeting():
    """The line the sketch in this repo would send on reboot.

    Used by the simulator, so that a simulated board announces the same
    firmware as a flashed one rather than a hand-copied constant that
    drifts the first time either number changes.
    """
    return {
        "hello": "colloquy of mobiles",
        "firmware": sketch_firmware_version(),
        "baudrate": sketch_baudrate(),
    }


def parse_greeting(line):
    """What the board said about itself, or None if that was not a board.

    Takes bytes off the wire or a str. A v1 board's bare "Hello!" is
    recognised and answered with LEGACY_GREETING, so the version check
    below gets something to complain about instead of a silence.
    """
    if isinstance(line, bytes):
        line = line.decode("utf-8", "replace")
    line = line.strip()
    if not line:
        return None
    if line.encode("utf-8", "replace") == LEGACY_HELLO:
        return dict(LEGACY_GREETING)
    try:
        greeting = json.loads(line)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(greeting, dict) or "firmware" not in greeting:
        return None
    return greeting


def baudrate_problems(params_baudrate):
    """Is params.json about to open the port at the rate the sketch sets?

    This is the check that costs nothing and catches the most: it needs no
    board, no port and no power, and it is the mismatch that happens by
    itself, because the two numbers live in two files that are edited on
    two different occasions.
    """
    expected = sketch_baudrate()
    if params_baudrate == expected:
        return []
    return [
        f"params.json opens the Arduino at {params_baudrate} baud, but the "
        f"sketch in this repo runs at {expected} "
        f"({SKETCH_PATH.name}, #define SERIAL_BAUDRATE). Nothing legible "
        f"will cross that link. Fix the number on the params page, or "
        f"flash a sketch that matches it."
    ]


def greeting_problems(greeting, params_baudrate):
    """Is the board on the other end one this driver can drive?

    `greeting` is what parse_greeting() made of the board's first line.
    """
    found = []
    version = greeting.get("firmware")
    if not isinstance(version, int) or version < MINIMUM_FIRMWARE_VERSION:
        found.append(
            f"the board is running firmware {version}, and this driver "
            f"needs at least {MINIMUM_FIRMWARE_VERSION}. Flash "
            f"{SKETCH_PATH.name} (firmware {sketch_firmware_version()}) "
            f"onto it."
        )

    board_baudrate = greeting.get("baudrate")
    if isinstance(board_baudrate, int) and board_baudrate != params_baudrate:
        found.append(
            f"the board says it is running at {board_baudrate} baud and "
            f"this port was opened at {params_baudrate}. One of the two is "
            f"from before the other was changed."
        )
    return found


def problems(params_baudrate, greeting=None):
    """Everything wrong with the link, in words, or an empty list.

    Called with no greeting before the port is opened (there is nothing to
    greet yet) and with one after, so the same call site reads both halves
    of the check.
    """
    found = baudrate_problems(params_baudrate)
    if greeting is not None:
        found += greeting_problems(greeting, params_baudrate)
    return found


def describe(greeting):
    """One line for the page, saying what is on the other end."""
    if greeting is None:
        return "not asked yet"
    return (
        f"firmware {greeting.get('firmware', '?')} "
        f"at {greeting.get('baudrate', '?')} baud"
    )
