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

**The two now judge differently, and the levels are why they still
agree.** The sketch calls a tone heard on an absolute rise of 4.0; this
calls it heard on a *multiple* of its own silence (see `is_heard`). That
is not drift - the sketch is a closed loop with a speaker six inches from
a microphone, and this is a room. A level means the same thing in both;
what a level has to reach to be believed is a property of the
arrangement, not of the arithmetic.
"""
from math import cos, pi, sin, sqrt
from typing import Iterable, Sequence

# How much a bin has to rise over its own silence before the tone is
# called heard, as a **multiple** of that silence rather than a difference
# from it.
#
# It was an absolute 4.0, carried over from the board, and on the first
# real run across a room it called every one of five plainly audible tones
# unheard: the loudest rise measured was 1.9 where 4.0 was wanted
# (2026_09_10_11h_52min_31s, still in `local/test results/`). Nothing else
# in that run was out of place - each tone landed in its own bin and
# nowhere else, 0.3 to 0.5s after its own mark - so the threshold was the
# whole of the fault. Six inches from a speaker is not a room, and the
# absolute number was a fact about the first arrangement being read as a
# fact about the second.
#
# A multiple is also the right shape for the question. The MAX9814's gain
# control moves the whole scale, and the floor differed by three times
# between pitches in that one run, so "louder than the room" is a ratio
# and never was a difference. In that run the five tones reached 12x to
# 160x their own floors, and the loudest silent block reached 6.3x, so 8
# sits between the two with the nearest real tone half as far again above
# it as the worst noise is below.
HEARD_RATIO = 8.0

# A silence quieter than this is not a reference worth dividing by: a
# floor near zero makes any multiple reachable by noise alone. So the
# floor is clamped up to it before the ratio is taken.
#
# 0.01 is the **median** silent reading of that same run (220 readings
# over 44 silent blocks: 0.0005 low, 0.0107 median, 0.0635 high). It is
# therefore a description of one measured room on one microphone, not a
# figure with a datasheet behind it - the distinction `SUPPLY_SETUP.md`
# was written the hard way. Raising it is a deliberate press against
# another measurement.
QUIET_FLOOR = 0.01

# The loudest a tone has actually been measured at, as a multiple of its
# own floor: 160x, at 6250 Hz, in the run of 2026-09-10. Rounded down to
# 120 because the number is wanted as "about how loud a tone gets", and it
# is used for one thing - deciding how much of a tone may spill into a
# neighbouring bin before that neighbour reads as a tone of its own.
LOUD_TONE = 120.0

# So: a pitch that takes this fraction of another's tone is a pitch that
# will be called heard when only its neighbour was played. It falls out of
# the two constants above rather than being chosen - at 8/120 a tone at
# LOUD_TONE puts exactly HEARD_RATIO into it - which is what keeps the
# warning and the verdict from drifting apart.
LEAK_LIMIT = HEARD_RATIO / LOUD_TONE


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


def bins_apart(first: float, second: float, sample_rate: float,
               count: int) -> int:
    """How many bins separate two pitches in a window this long.

    The number that says whether two tones can be told apart, and it is a
    property of the *capture* rather than of the pair: the same two
    frequencies are neighbours in a short window and separate in a long
    one. A rectangular window's sidelobes fall off slowly - a tone one bin
    away still puts about a quarter of itself in its neighbour, and even
    eight bins away it leaves a few percent - so this is a sliding scale
    and not a threshold. `pytest_tests` measures the whole curve against a
    generated signal.
    """
    return abs(
        bin_index(first, sample_rate, count)
        - bin_index(second, sample_rate, count)
    )


def leakage(hz: float, into_hz: float, sample_rate: float,
            count: int) -> float:
    """How much of a tone at `hz` shows up in the bin `into_hz` belongs to.

    A fraction of the tone's own bin, so 0.27 means a quarter of it lands
    somewhere it was not played.

    **This, not the distance between them, is what decides whether two
    pitches can be told apart** - which is the opposite of what counting
    bins suggests, and worth stating because counting bins is the obvious
    thing to do. A rectangular window is exactly orthogonal only at its own
    basis frequencies: a tone sitting **on** a bin centre puts nothing
    anywhere else, and one sitting half a bin off smears into every bin
    there is. So 1000 Hz, which lands 0.38 of a bin below centre here, puts
    5.7% into a pitch seven bins away, while 1050 Hz, which lands almost
    exactly on one, puts 0.9% into a pitch five bins away. Distance barely
    enters into it; the offset does.

    It is the Dirichlet kernel of that window - `sin(pi d) / sin(pi d / N)`
    at a distance `d` in bins - rather than a measurement, because the page
    asks it of every pair on every view and synthesising a sine to find out
    would be absurd. `pytest_tests` checks it against a generated signal,
    where it agrees to about a point.
    """
    if sample_rate <= 0 or count <= 0:
        return 0.0

    exact = count * hz / sample_rate
    own = round(exact)
    other = bin_index(into_hz, sample_rate, count)
    if other == own:
        return 1.0

    def response(index: int) -> float:
        distance = exact - index
        if abs(distance) < 1e-12:
            return float(count)
        return abs(sin(pi * distance)) / abs(sin(pi * distance / count))

    strength = response(own)
    if strength <= 0.0:
        return 0.0
    return response(other) / strength


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


def effective_floor(floor: float, quiet_floor: float = QUIET_FLOOR) -> float:
    """The silence a rise is measured against, never quieter than
    `quiet_floor` - see that constant on why a near-zero one cannot be
    divided by."""
    return max(floor, quiet_floor)


def times_its_floor(level: float, floor: float,
                    quiet_floor: float = QUIET_FLOOR) -> float:
    """How many times its own silence this bin is reading.

    The number the verdict is made on, so it is the number the page shows:
    a difference beside a ratio verdict would be an invitation to argue
    with the answer using the wrong arithmetic.
    """
    return level / effective_floor(floor, quiet_floor)


def is_heard(level: float, floor: float, ratio: float = HEARD_RATIO,
             quiet_floor: float = QUIET_FLOOR) -> bool:
    """Did this bin rise over its own silence by enough to believe?

    The rise is the only number worth believing, and it is a *multiple*.
    A MAX9814 has automatic gain control, so an absolute level says
    nothing; what it can say is that this frequency is some number of
    times louder than it was a moment ago, at a gain that has not had time
    to move.

    **Where this is weakest is a loud room**, and it is worth knowing
    before trusting a "not heard": a noisy floor is a bigger number to be
    a multiple of, so the same tone reaches a smaller ratio. The run this
    was set from was a quiet one. A verdict here is never the measurement
    anyway - somebody hearing the tone is, which is why this is a manual
    test.
    """
    return level >= effective_floor(floor, quiet_floor) * ratio
