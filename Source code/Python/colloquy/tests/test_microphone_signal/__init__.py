# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_microphone_signal/__init__.py

"""Is a microphone producing a signal at all?

Every other test of the sound channel reads the **analyser**, which is
the next link along from the microphone, so none of them can answer
this. `test_audio_loop` grades the twenty-five-verdict grid and
`test_audio_bringup` takes the chain apart by arranging for the faults
to have different shapes - but both of them are looking at seven band
values out of an MSGEQ7, and a microphone producing nothing looks
exactly like a microphone whose signal never reaches the MSGEQ7 from
there. `diagnosis.py` says as much about itself: three faults it cannot
separate, and it asks a person to listen rather than pretending
otherwise.

**This test cuts the chain at the MSGEQ7's input**, which is the one
place it can usefully be cut, for two reasons that are both about this
board rather than about testing in general:

- The microphone wire arrives on `J11`'s **odd** pin and nothing at all
  is fitted between it and the DSUB - `as built` section 6, "no
  microphone conditioning of any kind". So the odd pin *is* the
  MAX9814's output, reachable with a clip.
- The MSGEQ7's own support network is the one part of this design
  recorded nowhere in this repository (`next pcb` keeps it in its own
  BOM section for exactly that reason). It is therefore the most likely
  thing to be wrong and the least likely thing to be caught by anything
  reading its output.

**The instrument is your eyes on the Arduino IDE's Serial Plotter**, and
that is why this is a manual test rather than an autotest. Music from a
phone played into a body paints a shape anybody recognises in a second;
no arrangement of band numbers is as convincing, and none of it can be
written to a file by this process, because the trace is on a port this
process is deliberately not holding. See `plotter setup`, which hangs
here for `SUPPLY_SETUP.md`'s reason - the moment somebody needs telling
is the moment they are about to clip a lead onto something.

**What the run itself does is the other half of the split.** While you
play music, it holds every speaker silent and reads all five analyser
modules over and over, showing what each one makes of the same sound.
Put beside the plotter, that is the whole diagnosis on one screen:

| plotter | analyser bands | where the fault is |
|---|---|---|
| moves with the music | move too | not here - go on to `test audio bringup` |
| moves with the music | flat | between the microphone wire and the MSGEQ7: its input network, its supply, or the strobe |
| flat | flat | the microphone, its supply, or the wire back to the body |

Nothing is written down, and that is deliberate rather than an omission.
Half of this measurement is on a screen this software cannot see, so a
file holding only the other half would be a record of the half that was
never in doubt.
"""
from time import time

from colloquy.base_thread import BaseThread
from colloquy.drivers import audio
from colloquy.ui import leaves

from .plotter_document import MicrophonePlotter


class TestMicrophoneSignal(BaseThread):
    """Every ear read on a loop, while you play music at one of them."""

    scenario_names = ("microphone-signal-test",)

    # Twice a second. The MSGEQ7 holds a peak with its own decay and the
    # firmware throws ten sweeps away before the one it returns, so a
    # sweep costs about eight milliseconds and asking faster than this
    # would buy nothing but a busier link. Much slower and a passage of
    # music passes between two readings.
    READ_INTERVAL = 0.5

    def __init__(self, owner):
        super().__init__(owner=owner)

        # How to wire it, which of the two ways to do it, and what each
        # shape on the plot means.
        self._document = MicrophonePlotter(owner=self)

        self._last = None
        self._peaks = {}
        self._sweeps = 0
        self._outcome = None
        self._last_read_at = 0.0

    @property
    def name(self):
        return "test microphone signal"

    @property
    def wired_bodies(self):
        """The bodies whose analyser input is actually connected.

        Read on every use rather than kept, as everywhere else: an
        unwired analyser input is a floating ADC pin, and a floating pin
        does not read silence - it reads garbage. Which bodies those are
        changes as channels go in, and that list is the one place it is
        said.
        """
        return tuple(self.colloquy.params["audio"]["wired bodies"])

    # --- the run ----------------------------------------------------------

    def setup(self):
        self._last = None
        self._peaks = {}
        self._sweeps = 0
        self._outcome = None
        self._last_read_at = 0.0

        # The room has to hold only the sound you are playing into it.
        # The piece's own five tones would be picked up by every module
        # and would make the analyser half of this unreadable - and a
        # body singing while you hold a phone to its microphone is the
        # piece hearing itself, which is a different test entirely
        # (`test audio loop`).
        try:
            self.drivers.audio.silence()
        except Exception as error:
            self._refuse(f"could not silence the speakers: {error}")

    def setdown(self):
        # Nothing to put back. Nothing moved, nothing was lit, and the
        # speakers are meant to be left silent.
        pass

    def loop(self):
        now = time()
        if (now - self._last_read_at) < self.READ_INTERVAL:
            return
        self._last_read_at = now

        try:
            readings = self.drivers.audio.read_all()
        except Exception as error:
            # Almost always one thing, and it is worth naming rather than
            # letting it arrive as a traceback: the installation's own
            # Mega is running the plotter sketch instead of firmware 4,
            # which is what the second of the two wiring routes does to
            # it. That route gives up this half of the test by
            # construction - see `plotter setup`.
            self._refuse(f"could not read the analysers: {error}")
            return

        self._last = readings
        for name, values in readings.items():
            previous = self._peaks.get(name)
            if previous is None:
                self._peaks[name] = values
            else:
                self._peaks[name] = tuple(map(max, previous, values))
        self._sweeps += 1

    def _refuse(self, reason):
        self._outcome = f"stopped: {reason}"
        self.log(self._outcome)
        self.stop()

    def forget_the_peaks(self, request=None):
        """Throw the running maxima away.

        Worth a button because a peak is cumulative and the whole use of
        it is comparing one body against another: a spike from clipping
        the probe on, or from the first track being louder than the
        second, sits in that column for the rest of the run and quietly
        makes one ear look better than its neighbour.
        """
        self._peaks = {}
        return "peaks forgotten"

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        return self._with_scenarios(
            {
                self._document.name: self._document,
                "forget the peaks": self.forget_the_peaks,
            }
        )

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        # Said before any number, as everywhere in the sound channel. The
        # stand-in answers a sweep with entirely plausible numbers, so a
        # simulated run and a real one read alike - and there is no
        # phone and no microphone anywhere in a simulated one.
        leaf(
            "board",
            "the stand-in - there is no microphone behind these numbers"
            if self.drivers.arduino.is_using_the_stand_in
            else "a real board on this lead",
        )
        wired = self.wired_bodies
        leaf("wired bodies", ", ".join(wired) or "none")
        unwired = [name for name in audio.BODIES if name not in wired]
        if unwired:
            leaf(
                "not wired",
                f"{', '.join(unwired)} - a floating ADC pin reads garbage "
                "rather than silence, so ignore those rows",
            )

        leaf(
            "the other half",
            "the trace in the Arduino IDE's Serial Plotter. Bands that move "
            "with the music say the whole chain works; bands that stay flat "
            "while the plotter moves put the fault between the microphone "
            "wire and the MSGEQ7. See 'plotter setup'.",
        )

        if self._outcome is not None:
            leaf("outcome", self._outcome)

        if self._last is None:
            leaf("sweeps", "none yet - press start")
            return states

        leaf("sweeps", self._sweeps)
        leaf("bands", " ".join(f"{hz}Hz" for hz in audio.BANDS_HZ))
        for name in audio.BODIES:
            leaf(name, " ".join(str(value) for value in self._last[name]))
            leaf(
                f"{name} peak",
                " ".join(str(value) for value in self._peaks.get(name, ())),
            )
        return states
