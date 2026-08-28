# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware_tests/test_audio_teardown.py

"""Neither audio test may walk away leaving a body making a noise.

Observed on the bench, 2026-08-28: `test audio bringup` finished, its CSV
showed a clean three-phase run, and male1's speaker still read
`sounding` afterwards. Both tests' `setdown` called `self.audio.silence()`
bare, so anything raising out of it took the rest of the teardown with
it - the tone stayed on, the CSV was left open, and
`BaseThread._run_in_context` never reached the `stop()` that follows its
`setdown()`.

A dropped link is exactly when that happens, and this is the board whose
5 V browns out under the amplifiers (`hardware > electronics > dirty
rework`, section 0). It is also the worst possible moment for it: a strip
left lit is visible from the door, and a body left humming at 160 Hz in
an empty room is not something anybody notices until the morning - which
is the reasoning `Colloquy.silence_speakers` was written with, and why
both tests now call that one rather than silencing for themselves.
"""
from types import SimpleNamespace

import pytest

# Renamed on import: pytest tries to collect anything called Test* and
# then warns that it cannot, because both take a constructor.
from colloquy.tests.test_audio_bringup import TestAudioBringup as BringupTest
from colloquy.tests.test_audio_loop import TestAudioLoop as LoopTest

TESTS = (BringupTest, LoopTest)
IDS = ("bringup", "loop")


class Recorder:
    """Stands in for the root's never-raising silencer and the CSV."""

    def __init__(self, silence_raises=False):
        self.silenced = 0
        self.closed = 0
        self._silence_raises = silence_raises

    def silence_speakers(self):
        self.silenced += 1
        if self._silence_raises:
            raise RuntimeError("the link dropped while silencing")

    def close(self):
        self.closed += 1


def double(recorder):
    return SimpleNamespace(
        _start_time=1.0,
        _current="male1",
        colloquy=recorder,
        _file=recorder,
    )


@pytest.mark.parametrize("test", TESTS, ids=IDS)
def test_the_teardown_silences_every_speaker(test):
    recorder = Recorder()

    test.setdown(double(recorder))

    assert recorder.silenced == 1


@pytest.mark.parametrize("test", TESTS, ids=IDS)
def test_the_csv_is_closed_even_if_silencing_blows_up(test):
    """The `finally` this file exists for. Losing the run's data on top of
    leaving a tone on is two faults from one dropped link."""
    recorder = Recorder(silence_raises=True)

    with pytest.raises(RuntimeError):
        test.setdown(double(recorder))

    assert recorder.closed == 1


@pytest.mark.parametrize("test", TESTS, ids=IDS)
def test_it_silences_through_the_one_that_never_raises(test):
    """Not `self.audio.silence()`. The difference is the whole fix: that
    one raises on a dropped link, and this is called from a teardown that
    has a stop() waiting behind it."""
    recorder = Recorder()
    node = double(recorder)
    node.audio = SimpleNamespace(
        silence=lambda: pytest.fail("silenced the raising way")
    )

    test.setdown(node)

    assert recorder.silenced == 1


@pytest.mark.parametrize("test", TESTS, ids=IDS)
def test_a_run_with_no_file_still_silences(test):
    """A run refused before it opened one - `setup` can refuse on an
    unwired body list or a port that is not there."""
    recorder = Recorder()
    node = double(recorder)
    node._file = None

    test.setdown(node)

    assert recorder.silenced == 1
