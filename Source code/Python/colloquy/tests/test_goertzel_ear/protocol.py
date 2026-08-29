# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_goertzel_ear/protocol.py

"""What the ear board says, and how to read it.

Kept apart from the test for the reason `test_audio_subsystem/protocol.py`
is: parsing a board's replies is pure text work that can be tested
without a board, and the test around it is threads and serial ports that
cannot.

Every reply from `goertzel_ear.ino` is one line beginning with a keyword
and then `name=value` pairs, so this does not have to know the prose:

    test hz=1000 bin=1003.9 floor=1.20 tone=41.80 rise=40.60 heard=1 fs=19230
    reading hz=1000 bin=1003.9 level=41.80 fs=19230
"""
from typing import NamedTuple

# The installation's five, which is what a sweep walks. Not imported from
# `drivers/audio.py`: this board is a bench instrument and can be pointed
# at any frequency, and the day those five change is not a day this
# stops meaning anything.
PITCHES = (160, 400, 1000, 2500, 6250)


class Reading(NamedTuple):
    """One pitch, measured against its own silence."""

    hz: int
    bin_hz: float
    floor: float
    tone: float
    rise: float
    heard: bool
    sample_rate: float

    @property
    def verdict(self) -> str:
        return "heard" if self.heard else "not heard"


def fields(line):
    """The `name=value` pairs in a reply, as a dict of strings."""
    found = {}
    for piece in line.split():
        if "=" not in piece:
            continue
        name, _, value = piece.partition("=")
        found[name] = value
    return found


def parse_test(line):
    """One `test ...` line as a Reading, or None if it is not one.

    None rather than raising: a sweep's replies are interleaved with the
    board's own chatter and its closing `sweep done`, and a line that is
    not a reading is the ordinary case rather than a fault.
    """
    if not line.startswith("test "):
        return None
    values = fields(line)
    try:
        return Reading(
            hz=int(values["hz"]),
            bin_hz=float(values["bin"]),
            floor=float(values["floor"]),
            tone=float(values["tone"]),
            rise=float(values["rise"]),
            heard=values["heard"] == "1",
            sample_rate=float(values["fs"]),
        )
    except (KeyError, ValueError):
        return None


def summarise(readings):
    """One line for the page: what was heard, and what was not."""
    if not readings:
        return "nothing measured - the board answered no readings"

    heard = [r for r in readings if r.heard]
    if len(heard) == len(readings):
        weakest = min(readings, key=lambda r: r.rise)
        return (
            f"all {len(readings)} heard - weakest {weakest.hz} Hz "
            f"at +{weakest.rise:.1f}"
        )

    missing = ", ".join(f"{r.hz} Hz" for r in readings if not r.heard)
    return f"{len(heard)}/{len(readings)} heard - nothing at {missing}"


def bin_width(sample_rate, samples=512):
    """How wide the bin is, which is how well two tones can be told apart.

    The sketch captures `samples` points, so a bin is `fs / samples` wide -
    about 37 Hz at the rate a Mega's ADC gives. The closest two pitches
    this piece uses are 160 Hz apart.
    """
    return sample_rate / samples
