"""The manual test that reads a microphone before the analyser gets it.

Half of this test is a trace on a screen and cannot be checked from
here. What can be, and what these pin, is the half that runs in the
process: that a sweep is turned into live rows and a running peak, that
the peak is per band rather than per body, and above all that the two
ways this run can fail come back as a sentence rather than as a
traceback.

That last one is not a detail. The second of the two wiring routes puts
the plotter sketch onto the installation's own Mega, which leaves this
run with no board to read - so "the analysers cannot be read" is an
expected outcome of following the instructions, and a `SerialException`
out of a command has already twice taken the whole server down with the
pages that would have fixed it (CLAUDE.md, `CommandFailed`).

Nothing here starts a thread; `setup` and `loop` are called directly,
against doubles, per conftest.
"""
from types import SimpleNamespace

import pytest

from colloquy.drivers import audio
# Aliased, as the sibling files do: pytest tries to collect any class
# whose name starts with Test, and warns about every one that has a
# constructor - which every node in this tree has.
from colloquy.tests.test_microphone_signal import (
    TestMicrophoneSignal as MicrophoneTest,
)
from colloquy.tests.test_microphone_signal.plotter_document import (
    MicrophonePlotter,
)


class FakeAllAudio:
    """`drivers.audio` - one sweep of five ears, and one silence."""

    def __init__(self, sweeps=(), fails_with=None):
        self._sweeps = list(sweeps)
        self._fails_with = fails_with
        self.silenced = 0

    def silence(self):
        self.silenced += 1

    def read_all(self):
        if self._fails_with is not None:
            raise self._fails_with
        return self._sweeps.pop(0)


def a_sweep(**overrides):
    """Seven bands for each of the five bodies, all zero unless named."""
    return {name: overrides.get(name, (0,) * 7) for name in audio.BODIES}


def runner(audio_double, **extra):
    """A double carrying only what `setup`/`loop` touch."""
    attributes = dict(
        READ_INTERVAL=MicrophoneTest.READ_INTERVAL,
        drivers=SimpleNamespace(audio=audio_double),
        _last=None,
        _peaks={},
        _sweeps=0,
        _outcome=None,
        _last_read_at=0.0,
        log=lambda message: None,
        _refuse=lambda reason: None,
    )
    attributes.update(extra)
    return SimpleNamespace(**attributes)


@pytest.fixture
def node(stub_factory):
    """The real node, built against a stub owner.

    Safe to construct - it opens no file and touches no hardware in
    __init__ - and needed for the parts that are about where things
    hang rather than about what the loop does.
    """
    return MicrophoneTest(owner=stub_factory())


# --- what it is and where its document lives ------------------------------


def test_it_is_named_for_the_thing_it_looks_at(node):
    # Not "test microphone", which would read as a test of the whole
    # hearing chain - which is `test audio loop`, and which this one
    # exists precisely to stop being confused with.
    assert node.name == "test microphone signal"


def test_the_plotter_setup_hangs_off_this_test_and_nowhere_else(node):
    # Same arrangement as `supply setup` and `hardware setup`: the moment
    # somebody needs telling is the moment they are about to clip a lead
    # onto a connector.
    assert node.snapshot_children["plotter setup"] is node._document
    assert MicrophonePlotter.folder.name == "test_microphone_signal"
    assert node._document.file_path.is_file()
    assert node._document.read().startswith("#")


def test_it_declares_a_scenario_and_offers_it_beside_start(node):
    assert node.scenario_names == ("microphone-signal-test",)
    assert "scenarios" in node.snapshot_children


def test_the_sketch_it_describes_is_in_the_repository():
    # The document is useless without it, and a sketch folder is exactly
    # the kind of thing that gets moved without anything noticing.
    from pathlib import Path

    sketch = (
        Path(__file__).resolve().parents[3]
        / "Arduino"
        / "microphone_plotter"
        / "microphone_plotter.ino"
    )
    assert sketch.is_file()


# --- silencing before reading ---------------------------------------------


def test_setup_silences_every_speaker_first():
    """The room must hold only the sound being played into it.

    Five of the piece's own tones would be picked up by every module,
    and a body singing while a phone is held to its microphone is the
    piece hearing itself - a different test entirely.
    """
    ears = FakeAllAudio()
    fake = runner(ears)

    MicrophoneTest.setup(fake)

    assert ears.silenced == 1


def test_a_link_that_cannot_be_silenced_stops_the_run_with_a_sentence():
    ears = FakeAllAudio()
    ears.silence = _raising(RuntimeError("no link"))
    stopped = []
    fake = runner(ears, _refuse=stopped.append)

    MicrophoneTest.setup(fake)

    assert len(stopped) == 1
    assert "no link" in stopped[0]


# --- one sweep at a time --------------------------------------------------


def test_a_sweep_becomes_the_live_row_for_every_body():
    ears = FakeAllAudio([a_sweep(female1=(1, 2, 3, 4, 5, 6, 7))])
    fake = runner(ears)

    MicrophoneTest.loop(fake)

    assert fake._last["female1"] == (1, 2, 3, 4, 5, 6, 7)
    assert set(fake._last) == set(audio.BODIES)
    assert fake._sweeps == 1


def test_it_reads_no_faster_than_its_own_interval():
    """A sweep costs about eight milliseconds of the link and the MSGEQ7
    throws ten sweeps away before the one it returns, so asking faster
    buys nothing but a busier board."""
    ears = FakeAllAudio([a_sweep()])
    fake = runner(ears)

    MicrophoneTest.loop(fake)
    MicrophoneTest.loop(fake)  # immediately after: too soon

    assert fake._sweeps == 1


def test_the_peak_is_kept_band_by_band_not_sweep_by_sweep():
    """The peak is what one ear is compared against another with, so it
    has to be the highest each *band* has reached - not the whole of
    whichever sweep happened to be loudest overall."""
    ears = FakeAllAudio(
        [
            a_sweep(male1=(9, 0, 0, 0, 0, 0, 0)),
            a_sweep(male1=(0, 8, 0, 0, 0, 0, 0)),
        ]
    )
    fake = runner(ears)

    MicrophoneTest.loop(fake)
    fake._last_read_at = 0.0
    MicrophoneTest.loop(fake)

    assert fake._peaks["male1"] == (9, 8, 0, 0, 0, 0, 0)
    assert fake._last["male1"] == (0, 8, 0, 0, 0, 0, 0)


def test_forgetting_the_peaks_leaves_the_live_rows_alone():
    """Pressed when something has moved between one comparison and the
    next - a probe reclipped, a louder track - and a spike left in one
    column quietly makes one ear look better than its neighbour."""
    fake = runner(FakeAllAudio())
    fake._peaks = {"male1": (9,) * 7}
    fake._last = {"male1": (1,) * 7}

    assert MicrophoneTest.forget_the_peaks(fake) == "peaks forgotten"
    assert fake._peaks == {}
    assert fake._last == {"male1": (1,) * 7}


# --- the failure that following the instructions produces -----------------


def test_a_board_that_cannot_be_read_stops_with_a_sentence_not_a_traceback():
    """The expected outcome of the second wiring route.

    That route flashes the plotter sketch onto the installation's own
    Mega, so there is no firmware 4 on the other end of the link and no
    sweep to be had. It is a documented way to use this test, not a
    crash - and an exception out of a command has twice taken the whole
    server down along with the page that would have fixed it.
    """
    ears = FakeAllAudio(fails_with=OSError("could not open port 'COM4'"))
    stopped = []
    fake = runner(ears, _refuse=stopped.append)

    MicrophoneTest.loop(fake)

    assert len(stopped) == 1
    assert "COM4" in stopped[0]
    assert fake._sweeps == 0


def _raising(error):
    def raise_it(*args, **kwargs):
        raise error

    return raise_it
