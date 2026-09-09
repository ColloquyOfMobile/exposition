# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_goertzel_ear/goertzel.py

"""How loud one frequency is in a block of samples.

The whole of the arithmetic that used to run on the board, moved to the
machine that now has the samples. It is a page of it: a Goertzel is one
multiply-accumulate per sample per frequency, which is why it was ever a
candidate for a Pro Mini, and why running it here costs nothing at all.

**Why it is worth having as its own module.** Two reasons, and the second
is the one that put it under mypy. It is pure - samples in, a number out,
no port, no thread, no clock - so it can be checked against a signal
generated in the test itself, which is the only way to know the answer is
right rather than merely plausible. And its confusions are real: a
frequency in hertz, an index into the bins, a count of samples and a
sample rate are four numbers that all read as "about a thousand" and mean
entirely different things. `drivers/audio.py` earned its place on the
same list for the same reason.

**Two arrangements of the same idea, and they must agree.**
`Source code/Arduino/goertzel_ear/` runs this on an AVR over its own
samples; this runs it on a PC over samples from
`Source code/Arduino/microphone_sampler/`. Same normalisation (divided by
the sample count) and same mean removal, so a level printed by one is
comparable with a level printed by the other. That is deliberate: the
board's numbers are in `HARDWARE_SETUP.md` and in this repository's
history, and a rewrite that quietly rescaled them would make every one of
them a lie.
"""
from math import cos, pi, sqrt
from typing import Iterable, Sequence

# How much a bin has to rise over its own silence before the tone is
# called heard. Blunt on purpose, and the same number the board uses, in
# the same units - see the module docstring on why the two scales match.
HEARD_MARGIN = 4.0


def bin_index(hz: float, sample_rate: float, count: int) -> int:
    """Which basis frequency of a `count`-sample window is nearest `hz`.

    Rounded to a whole number of cycles in the window so the bin sits
    exactly on a basis frequency and nothing is lost to scalloping - a
    tone falling between two bins reads low in both, which would look
    exactly like a microphone that could not hear it. The frequency
    actually measured is therefore `bin_hz`, not `hz`, and the page shows
    it rather than hiding it.
    """
    if sample_rate <= 0 or count <= 0:
        return 0
    index = int(0.5 + (count * hz) / sample_rate)
    return max(1, min(index, count // 2 - 1))


def bin_hz(hz: float, sample_rate: float, count: int) -> float:
    """The frequency actually measured when `hz` is asked for."""
    if count <= 0:
        return 0.0
    return bin_index(hz, sample_rate, count) * sample_rate / count


def bin_width(sample_rate: float, count: int) -> float:
    """How wide a bin is, which is how well two tones can be told apart.

    `sample_rate / count` - about 37 Hz for 512 samples at the rate a
    Mega's ADC gives. The closest two pitches this piece uses are 160 Hz
    apart, so they are three bins clear of each other.
    """
    if count <= 0:
        return 0.0
    return sample_rate / count


def magnitude(samples: Sequence[int], hz: float, sample_rate: float) -> float:
    """The level of one frequency in this block, per sample.

    The microphone sits at mid-rail, so the block's own mean is the DC to
    take out; doing it here rather than with a capacitor keeps the input
    network to a wire. Dividing by the sample count is what makes a level
    from a 512-sample block comparable with one from any other length.
    """
    count = len(samples)
    if count == 0 or sample_rate <= 0:
        return 0.0

    index = bin_index(hz, sample_rate, count)
    omega = 2.0 * pi * index / count
    coefficient = 2.0 * cos(omega)

    mean = sum(samples) / count

    first = 0.0
    second = 0.0
    for sample in samples:
        current = (sample - mean) + coefficient * first - second
        second = first
        first = current

    power = first * first + second * second - coefficient * first * second
    if power < 0:
        power = 0.0
    return sqrt(power) / count


def magnitudes(
    samples: Sequence[int], pitches: Iterable[float], sample_rate: float
) -> dict[float, float]:
    """Every pitch measured in one block, keyed by the pitch asked for.

    This is the whole reason the samples cross the wire rather than a
    verdict. A Goertzel is one pass per frequency over samples already in
    hand, so five pitches out of one capture cost five passes over 512
    numbers and no extra sampling at all - the five readings are then of
    the *same instant*, which is the only way to say that the tone rose
    and the room did not.
    """
    return {hz: magnitude(samples, hz, sample_rate) for hz in pitches}


def is_heard(level: float, floor: float, margin: float = HEARD_MARGIN) -> bool:
    """Did this bin rise over its own silence by enough to believe?

    The rise is the only number worth believing. A MAX9814 has automatic
    gain control, so its absolute level says nothing; what it can say is
    that this frequency is louder than it was a moment ago, at a gain
    that has not had time to move.
    """
    return (level - floor) >= margin
