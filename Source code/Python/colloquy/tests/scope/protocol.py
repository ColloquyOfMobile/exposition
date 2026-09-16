# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/scope/protocol.py

"""The two-channel reply, and how to read it.

The scope asks the sampler board for `d` rather than `b`, and what comes
back is a different line with a keyword of its own:

    pair n=256 fs=9615.4 pins=A0,A1 512 511 514 509 ...

`n` is **pairs**, `fs` is per channel, and the samples are interleaved -
A0, A1, A0, A1. One converter behind a multiplexer means the two halves
of a pair are one conversion apart, about 52 us, rather than
simultaneous; `scope/__init__.py` says so on the page, because it is the
one thing about this arrangement that a reader could be wrong about
without noticing.

**A keyword of its own is the whole safety.** `b` and its `block ...`
reply belong to `test_goertzel_ear`, which runs five Goertzel bins over
what comes back. Handing that two interleaved microphones would not fail
- it would answer, wrongly, about a frequency nobody played. So neither
parser can accept the other's line, and this one is here rather than in
the ear's `protocol.py` for the same reason the command is separate.

Kept apart from the node because parsing is pure text work that can be
checked without a board, which is what `test_goertzel_ear/protocol.py`
already says about itself.
"""
from typing import NamedTuple

# The firmware that knows `d`. A board on 1 has A0 and nothing else, and
# it does not go quiet when asked for two channels - it answers
# `error commands: b | ?`, which is a perfectly good reply to a question
# it does not understand and parses here as "not a capture". Read as
# silence, that sends somebody to check a lead that was never the problem.
MINIMUM_FIRMWARE = 2

REFUSAL = "error"


class Pairs(NamedTuple):
    """One dual capture: two channels, and the rate each was taken at."""

    sample_rate: float
    names: tuple        # ("A0", "A1")
    channels: tuple     # one tuple of samples per name, same length

    @property
    def count(self):
        """Pairs, which is how many samples are in *each* channel."""
        return len(self.channels[0]) if self.channels else 0

    def extent(self, index):
        """Lowest and highest count on one channel, or None if it is
        empty. See `Scope._describe_channel` for what it is good for."""
        samples = self.channels[index]
        if not samples:
            return None
        return min(samples), max(samples)


def parse_pairs(line):
    """One `pair ...` line as `Pairs`, or None if it is not one.

    None rather than raising, for the reason the ear's parser gives: the
    reply to a command arrives among the board's greeting and whatever
    half line was in the buffer when the port opened, so a line that is
    not a capture is the ordinary case rather than a fault.

    A reply whose sample count disagrees with its own `n=` is dropped
    too, and here that matters more than it does for one channel: 512
    numbers do not fit in a serial buffer at once, so a read that gives up
    early yields a line that parses perfectly and is missing its end - and
    on an odd truncation the two channels would come apart, every A1
    landing where an A0 belongs. A silently swapped pair of microphones is
    the exact fault this test is used to find.
    """
    if not line.startswith("pair "):
        return None

    values = {}
    numbers = []
    for piece in line.split()[1:]:
        if "=" in piece:
            name, _, value = piece.partition("=")
            values[name] = value
            continue
        try:
            numbers.append(int(piece))
        except ValueError:
            return None

    try:
        expected = int(values["n"])
        sample_rate = float(values["fs"])
    except (KeyError, ValueError):
        return None

    names = tuple(values.get("pins", "A0,A1").split(","))
    if len(names) < 2 or sample_rate <= 0:
        return None
    if len(numbers) != expected * len(names):
        return None

    channels = tuple(
        tuple(numbers[offset :: len(names)]) for offset in range(len(names))
    )
    return Pairs(sample_rate=sample_rate, names=names, channels=channels)


def firmware_of(line):
    """The firmware version in a greeting or a status line, or None.

    The greeting is the one place the board says what it is, and it says
    it unprompted on every reboot - which is every time the port opens,
    since opening toggles DTR. So this costs nothing and is known before
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


def is_refusal(line):
    """Did the board answer that it does not know the command?

    Its own word for it, and the one reply that must not be read as
    silence: silence is a lead, a refusal is a sketch.
    """
    return bool(line) and line.startswith(REFUSAL)
