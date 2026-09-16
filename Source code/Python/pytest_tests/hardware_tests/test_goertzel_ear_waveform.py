# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware_tests/test_goertzel_ear_waveform.py

"""The block drawn as a shape, with no board and no page.

`waveform.py` is the same capture `goertzel.py` computes its bins from,
asked what it looks like instead of what is in it. It is pure arithmetic
on a `protocol.Block`, so all of it can be checked here.

What is worth pinning is the part that is easy to get right in a way that
lies: the x axis. A block is 27 ms and the graph's ticks carry one
decimal, so in seconds every label reads `0.0s` and the picture silently
stops saying when anything happened. Milliseconds are what make a period
countable, which is the whole reason for drawing it, so they are checked
against the sample rate the board measured rather than against a
constant.
"""
from math import pi, sin

import pytest

from colloquy.tests.test_goertzel_ear import protocol, waveform

SAMPLE_RATE = 19230.8
COUNT = 512


def block(hz=400, count=COUNT, sample_rate=SAMPLE_RATE):
    samples = tuple(
        int(512 + 100 * sin(2 * pi * hz * i / sample_rate)) for i in range(count)
    )
    return protocol.Block(sample_rate=sample_rate, samples=samples)


# --- the shape -----------------------------------------------------------


def test_every_sample_is_drawn():
    """No thinning here. `GraphView` decides what it draws; this hands
    over the block whole, and a capture is small enough that it can."""
    assert len(waveform.points(block())) == COUNT


def test_x_is_milliseconds_off_the_measured_rate():
    points = waveform.points(block())
    assert points[0][0] == 0.0
    # The second sample is one period of the sample rate later, in ms.
    assert points[1][0] == pytest.approx(1000.0 / SAMPLE_RATE)
    # And the last is the whole window, less that one step.
    assert points[-1][0] == pytest.approx(
        waveform.span_ms(block()) - 1000.0 / SAMPLE_RATE
    )


def test_the_window_is_twenty_seven_milliseconds():
    """512 samples at ~19.2 kSPS. The number that decides whether a tone
    has several cycles on the picture or part of one."""
    assert waveform.span_ms(block()) == pytest.approx(26.6, abs=0.1)


def test_y_is_the_raw_count():
    """Not scaled, not centred, not converted to volts - the ADC's own
    number, which is what every other reading in this test is in."""
    made = block()
    assert [value for _ms, value in waveform.points(made)] == list(made.samples)


def test_an_empty_block_draws_nothing():
    empty = protocol.Block(sample_rate=SAMPLE_RATE, samples=())
    assert waveform.points(empty) == []
    assert waveform.span_ms(empty) == 0.0


def test_a_rate_of_zero_is_not_a_division():
    """A board that has never captured reports fs=0. It cannot reach the
    parser, which refuses that line, but the node holds the last block
    and this must not be the thing that raises out of a render."""
    stopped = protocol.Block(sample_rate=0.0, samples=(1, 2, 3))
    assert waveform.points(stopped) == []
    assert waveform.samples_per_cycle(stopped, 400) == 0.0


# --- what is in the window -----------------------------------------------


def test_cycles_of_the_tone_being_played():
    """The reading that turns the picture into a check: at 400 Hz there
    are about eleven tops to count across the window."""
    assert waveform.cycles(block(), 400) == pytest.approx(10.6, abs=0.1)


def test_samples_per_cycle():
    assert waveform.samples_per_cycle(block(), 400) == pytest.approx(48.1, abs=0.1)


def test_a_legible_tone_is_not_warned_about():
    said = waveform.describe(block(), 400)
    assert "400 Hz" in said
    assert "too few" not in said


def test_a_tone_too_fast_to_look_like_a_wave_says_so():
    """6250 Hz is three samples a cycle at this rate. The bin is still
    right - a Goertzel needs two - but the drawing is not the signal's
    shape, and that looks exactly like a fault rather than a limit."""
    said = waveform.describe(block(), 6250)
    assert "too few" in said
    assert "bins are still right" in said


def test_the_ceiling_is_the_boards_rate_not_a_constant():
    """Where legibility runs out is `rate / 8`, so a board with a
    different prescaler moves it without an edit here."""
    ceiling = SAMPLE_RATE / waveform.LEGIBLE_SAMPLES_PER_CYCLE
    assert "too few" not in waveform.describe(block(), int(ceiling * 0.9))
    assert "too few" in waveform.describe(block(), int(ceiling * 1.1))


def test_describe_without_a_tone_says_only_what_was_captured():
    """Nothing is playing most of the time, and a sentence about cycles
    of None would be worse than no sentence."""
    said = waveform.describe(block(), None)
    assert "512 samples" in said
    assert "cycles" not in said


# --- the press -----------------------------------------------------------


def test_drawing_before_anything_was_captured_is_refused():
    """Instant, and reading only what is already in hand - the run may not
    be started, and the link must not be the thing that reaches for a
    serial port to find out.

    An unbound call with a double, per pytest_tests/conftest.py: building
    the test node needs the whole hardware graph behind it.
    """
    from types import SimpleNamespace

    from colloquy.tests.test_goertzel_ear import TestGoertzelEar

    nothing_yet = SimpleNamespace(_block=None)
    said = TestGoertzelEar._draw_the_waveform(nothing_yet)
    assert said.startswith("refused:")
    assert "start the test" in said
