# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_goertzel_ear/waveform.py

"""A block as a shape: the samples against the time they were taken at.

The samples are already here - `goertzel.py` runs five bins over them and
the page reports what it found - so this is the same capture asked a
different question. Every reading this test gives is a *number about* the
block; this is the block.

**It is worth having because a number cannot be recognised and a shape
can.** A bin level says a frequency is present, and it says the same
thing whether what is on the pin is a clean sine, a square, a clipped
mess or mains hum landing in the same bin. Somebody who can see 400 Hz as
ten cycles across a 27 ms window has settled in one glance a question
that no arrangement of bin levels ever settles, and `MICROPHONE_PLOTTER.md`
already makes the argument for the general case: "sound arriving is a
shape you recognise in a second".

This is the same instrument as `microphone_plotter`'s WAVE mode with the
one limitation of that mode removed. There, a burst is drawn by the
Arduino IDE's plotter, which has no time axis - it keeps a fixed number
of recent points, so the sample rate alone decides how many cycles are on
the screen, and the rate has to be tuned by hand to the tone. Here the
samples arrive with the rate they were taken at (the board measures it
rather than assuming it), so the x axis is real milliseconds and nothing
needs tuning to anything.

Pure arithmetic on a `protocol.Block`, kept out of the node for the
reason `protocol.py` is: it can be checked without a board.
"""

# Below this many samples to a cycle, a wave is present in the numbers
# and not recognisable as a wave by eye - the points are too far apart to
# join into a shape, and what gets drawn looks like a wobble at some
# frequency nobody played.
#
# Eight is the same figure `microphone_plotter`'s WAVE_POINTS_PER_CYCLE
# is set around, and for the same reason: it is about where the tops stop
# repeating visibly. At the sampler's ~19.2 kSPS it puts the ceiling at
# about 2.4 kHz, which is a fact about the board's prescaler and not
# about the microphone - the bins go on being right well above it, since
# a Goertzel needs only two samples a cycle and does not care what
# anything looks like.
LEGIBLE_SAMPLES_PER_CYCLE = 8


def points(block):
    """Every sample in the block, as (milliseconds, ADC count).

    Milliseconds because a block is 27 ms and the graph's x labels carry
    one decimal: in seconds every tick on the axis would read `0.0s`.
    That is what `GraphView`'s `x_unit` is for.

    A list rather than a lazy view, which is the opposite of what
    `Columns` exists for and is right at this size: 512 pairs is nothing,
    and the alternative - a view onto a tuple this function would have to
    keep anyway - would be machinery around no saving at all.
    """
    if not block.samples or block.sample_rate <= 0:
        return []
    step = 1000.0 / block.sample_rate
    return [(index * step, value) for index, value in enumerate(block.samples)]


def span_ms(block):
    """How long the whole capture lasted, in milliseconds."""
    if not block.samples or block.sample_rate <= 0:
        return 0.0
    return 1000.0 * block.count / block.sample_rate


def samples_per_cycle(block, hz):
    """How many samples fall across one cycle of `hz`."""
    if not hz or block.sample_rate <= 0:
        return 0.0
    return block.sample_rate / hz


def cycles(block, hz):
    """How many cycles of `hz` are in the window."""
    return span_ms(block) / 1000.0 * hz if hz else 0.0


def describe(block, hz=None):
    """One line for the page: what is in this window, and is it legible.

    `hz` is the tone being played, when one is - the whole of what makes
    the reading actionable. "27.0 ms at 19231 a second" says what was
    captured; "10.8 cycles of 400 Hz, 48 samples each" says what you
    should be able to count on the picture, which is the thing that turns
    a wobble into a confirmation.
    """
    parts = [
        f"{span_ms(block):.1f} ms, {block.count} samples at "
        f"{block.sample_rate:.0f} a second"
    ]
    if hz:
        per_cycle = samples_per_cycle(block, hz)
        parts.append(
            f"{cycles(block, hz):.1f} cycles of {hz} Hz, "
            f"{per_cycle:.0f} samples each"
        )
        if per_cycle < LEGIBLE_SAMPLES_PER_CYCLE:
            # Said rather than left to be seen, because what it looks
            # like is a fault: too few samples a cycle draws a wobble at
            # a frequency nobody played, which is exactly what a badly
            # wired microphone would draw too.
            parts.append(
                f"too few to look like a wave - under "
                f"{LEGIBLE_SAMPLES_PER_CYCLE} a cycle the shape is not "
                f"the signal's, though the bins are still right"
            )
    return " - ".join(parts)
