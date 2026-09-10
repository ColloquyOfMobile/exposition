# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_goertzel_ear/protocol.py

"""What the sampler board says, and how to read it.

Kept apart from the test for the reason `test_audio_subsystem/protocol.py`
is: parsing a board's replies is pure text work that can be checked
without a board, and the test around it is threads and serial ports that
cannot.

The board is `Source code/Arduino/microphone_sampler/` and every reply is
one line beginning with a keyword and then `name=value` pairs, so this
does not have to know the prose:

    microphone_sampler firmware=1 mic_pin=A0 n=512 fs=19230.8 baud=1000000
    status firmware=1 mic_pin=A0 n=512 fs=19230.8
    block n=512 fs=19230.8 512 511 514 509 ...

**A block carries samples and nothing else.** It says nothing about which
frequency, how loud, or whether anything was heard - those are questions
this end asks of the numbers, in `goertzel.py`. That is the change: the
board used to send a verdict and now sends the evidence.
"""
from typing import NamedTuple

# The installation's five, which is what the page offers a link for. Not
# imported from `drivers/audio.py`: this is a bench instrument and can be
# pointed at any frequency, and the day those five change is not a day
# this stops meaning anything.
PITCHES = (160, 400, 1000, 2500, 6250)


class Block(NamedTuple):
    """One capture: the samples, and the rate they were taken at."""

    sample_rate: float
    samples: tuple

    @property
    def count(self):
        return len(self.samples)

    @property
    def span(self):
        """Peak to peak, in ADC counts.

        Not a measurement of anything, and useful for exactly one thing:
        a span of zero is a pin with nothing on it, and a span pinned at
        the full 1023 is an input being clipped. Both look like a
        perfectly ordinary bin reading otherwise.
        """
        if not self.samples:
            return 0
        return max(self.samples) - min(self.samples)


def fields(line):
    """The `name=value` pairs in a reply, as a dict of strings."""
    found = {}
    for piece in line.split():
        if "=" not in piece:
            continue
        name, _, value = piece.partition("=")
        found[name] = value
    return found


def parse_block(line):
    """One `block ...` line as a Block, or None if it is not one.

    None rather than raising, for the reason every parser here returns
    None: the reply to a command arrives among the board's own greeting
    and whatever half line was left in the buffer when the port opened,
    and a line that is not a block is the ordinary case rather than a
    fault.

    A block whose sample count disagrees with its own `n=` is dropped
    too. That is not fussiness - it is the one shape a truncated line
    takes here. 512 numbers do not fit in a serial buffer at once, so a
    read that gives up early yields a line that parses perfectly and is
    missing its end, and a short window silently widens every bin.
    """
    if not line.startswith("block "):
        return None

    pieces = line.split()
    values = {}
    samples = []
    for piece in pieces[1:]:
        if "=" in piece:
            name, _, value = piece.partition("=")
            values[name] = value
            continue
        try:
            samples.append(int(piece))
        except ValueError:
            return None

    try:
        expected = int(values["n"])
        sample_rate = float(values["fs"])
    except (KeyError, ValueError):
        return None

    if expected != len(samples) or sample_rate <= 0:
        return None
    return Block(sample_rate=sample_rate, samples=tuple(samples))


class Reading(NamedTuple):
    """One pitch, measured against its own silence.

    Made on this end now rather than parsed off the board, but the same
    seven facts and the same units - see `goertzel.py` on why the scales
    were kept.
    """

    hz: int
    bin_hz: float
    floor: float
    level: float
    heard: bool
    sample_rate: float

    @property
    def rise(self) -> float:
        """The bare difference. Kept because it is what a level over a
        level *is*, and not what the verdict is made on - see `times`."""
        return self.level - self.floor

    @property
    def times(self) -> float:
        """How many times its own silence this bin reached, which is what
        `goertzel.is_heard` decides on."""
        from . import goertzel

        return goertzel.times_its_floor(self.level, self.floor)

    @property
    def verdict(self) -> str:
        return "heard" if self.heard else "not heard"


def summarise(readings):
    """One line for the page: what was heard, and what was not.

    Over the pitches that have actually been *played*, which is not the
    same as all five. One tone sounds at a time and somebody presses the
    links in whatever order they like, so a pitch nobody has played yet
    is an open question rather than a failure, and calling it "not heard"
    would be the test answering a question it was never asked.
    """
    if not readings:
        return "no pitch played yet - press one of the play links"

    heard = [r for r in readings if r.heard]
    if not heard:
        return f"nothing heard at any of the {len(readings)} pitches"
    if len(heard) == len(readings):
        weakest = min(readings, key=lambda r: r.times)
        return (
            f"all {len(readings)} heard - weakest {weakest.hz} Hz "
            f"at x{weakest.times:.1f} its floor"
        )

    missing = ", ".join(f"{r.hz} Hz" for r in readings if not r.heard)
    return f"{len(heard)}/{len(readings)} heard - nothing at {missing}"
