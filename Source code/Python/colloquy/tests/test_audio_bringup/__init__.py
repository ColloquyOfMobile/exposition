# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_audio_bringup/__init__.py

"""The first run after wiring an audio channel, and what to do when it fails.

`test_audio_loop` is the acceptance test: five voices, five ears,
twenty-five verdicts, run when everything is in. This is the one for the
afternoon the board comes back from the bench with two channels on it.

Two differences, and both matter on that afternoon:

- **It only looks at what is wired** (`params["audio"]["wired bodies"]`).
  An unwired analyser input is a floating ADC pin, and a floating ADC pin
  does not read silence - it reads whatever the neighbouring pin is
  doing. A five-channel test on a two-channel board reports twenty-one
  fictional failures and buries the two real answers among them.
- **It diagnoses.** The whole chain is one measurement - timer, pin,
  filter, divider, amplifier, speaker, air, microphone, MSGEQ7, ADC - so
  "silent" is nine possible faults. `diagnosis.py` takes them apart using
  the two facts that give faults different shapes: every ear hears every
  voice (so a tone heard by nobody is a speaking fault, and an ear that
  hears nothing while another hears everything is a hearing fault), and a
  tone lands in a *band*, which is frequency rather than geometry.

**What it does to the room.** Reads in silence, then holds each wired
voice in turn for a few seconds. Nothing turns and nothing lights up.
With two channels it is about twenty seconds end to end.

**The one thing it will ask you to do.** When a voice is heard by
nobody, it stops and asks you to listen while the tone is held. No
reading here can tell a tone that is not being generated from a tone
going into a dead amplifier - both are silence - and one second of
listening splits the chain in half. The report says which half to
believe either way.
"""

from datetime import datetime
from functools import partial
from time import time

from colloquy.base_thread import BaseThread
from colloquy.drivers import audio
from colloquy.ui import leaves

from . import diagnosis


class TestAudioBringup(BaseThread):
    scenario_names = ("audio-bringup-test",)

    # Long enough to hear it and place it in the room, short enough that
    # a two-channel run is over in twenty seconds.
    TONE_SECONDS = 4.0

    # After a tone changes, before its readings count. The MSGEQ7 is a
    # peak detector with its own decay and the firmware already throws
    # away ten sweeps per read for the same reason; this is the slower
    # half of it.
    SETTLE_SECONDS = 0.8

    # Silence is read for longer than a tone: every later verdict is a
    # rise over this floor, so it is the one measurement worth taking
    # more of.
    FLOOR_SECONDS = 5.0

    def __init__(self, owner, result_folder):
        super().__init__(owner=owner)

        self._bodies = {body.name: body for body in self.drivers.bodies}

        self._manual = {"silence": self._silence}
        for name in audio.BODIES_BY_PITCH:
            voice = audio.VOICES[name]
            self._manual[f"hold {name} ({voice['hz']} Hz, {voice['pin']})"] = partial(
                self._hold, name
            )
        self._manual["read every wired ear"] = self._read_now

        self._dir_path = result_folder / self.name
        if not self._dir_path.exists():
            self._dir_path.mkdir()

        self._file = None
        self._start_time = None
        self._queue = None
        self._current = None
        self._floor = None
        self._healths = []
        self._readings = []
        self._steps = []
        self._outcome = None
        self._last_read = None

    @property
    def name(self):
        return "test audio bringup"

    @property
    def audio(self):
        return self.drivers.audio

    @property
    def wired(self):
        """The bodies whose channel is actually built, in pitch order.

        Read from params on every use rather than at construction, so that
        adding the third channel tomorrow is an edit on the params page
        and not a restart. Filtered against the real table so a typo
        there cannot crash a run in the middle.
        """
        chosen = list(self.colloquy.params["audio"]["wired bodies"])
        return [name for name in audio.BODIES_BY_PITCH if name in chosen]

    @property
    def unknown_wired(self):
        """Names in params that are not bodies. Shown rather than ignored:
        a typo here silently drops a channel from the run."""
        known = set(audio.VOICES)
        return [
            name
            for name in self.colloquy.params["audio"]["wired bodies"]
            if name not in known
        ]

    # --- the manual commands ----------------------------------------------

    def _hold(self, name, request=None):
        """One voice on, everything else off - so the question 'where is
        that tone coming from' has one answer."""
        self.audio.silence()
        self._bodies[name].speaker.on()
        voice = audio.VOICES[name]
        return (
            f"{name} sounding: {voice['hz']} Hz out of {voice['pin']}. "
            "Listen for it, and put a scope on that pin if you cannot hear it."
        )

    def _silence(self, request=None):
        self.audio.silence()
        return "everything is quiet"

    def _read_now(self, request=None):
        """One sweep, printed. The quickest thing on the page: it says
        whether the ears answer at all, and it needs no run."""
        readings = self.audio.read_all()
        self._last_read = " | ".join(
            f"{name} (A{audio.module_of(name)}): "
            + " ".join(f"{value:4}" for value in readings[name])
            for name in self.wired
        )
        return self._last_read

    # --- the run ----------------------------------------------------------

    def run(self):
        now = datetime.now()
        file_path = (
            self._dir_path
            / f"{now.year}_{now.month:02}_{now.day:02}_{now.hour:02}h_"
            f"{now.minute:02}min_{now.second:02}s.csv"
        )
        run_with = self._file = file_path.open("a")
        super().run(run_with=run_with)

    def setup(self):
        self._start_time = time()
        self._healths = []
        self._readings = []
        self._steps = []
        self._outcome = None
        self._floor = None
        self._file.write(
            "seconds, sounding, listener, "
            + ", ".join(f"{hz} Hz" for hz in audio.BANDS_HZ)
            + "\n"
        )

        if not self.wired:
            self._refuse(
                "no bodies listed under params > audio > wired bodies - "
                "nothing to test"
            )
            return

        # Always, and first. A run that begins with something already
        # sounding measures its floor against that tone and then reports
        # every other body as silent.
        self.audio.silence()
        self._queue = [None] + list(self.wired)
        self._advance()

    def setdown(self):
        self._start_time = None
        self._current = None
        self.audio.silence()
        if self._file is not None:
            self._file.close()

    def _refuse(self, reason):
        self._outcome = f"refused: {reason}"
        self._steps = [reason]
        self.log(f"Refusing to run: {reason}")
        self.stop()

    def _advance(self):
        if not self._queue:
            self._current = None
            self._finish()
            self.stop()
            return
        self._current = self._queue.pop(0)

    def loop(self):
        if self._current is None and self._queue is None:
            return

        singer = self._current
        self.audio.silence()
        if singer is not None:
            self._bodies[singer].speaker.on()

        self._settle(self.SETTLE_SECONDS)
        seconds = self.FLOOR_SECONDS if singer is None else self.TONE_SECONDS
        sweeps = self._collect("silence" if singer is None else singer, seconds)

        if singer is None:
            self._floor = sweeps
            # Stage one, before a note is played: does each ear answer?
            # Everything after this is a rise over these numbers, so an
            # ear that is not answering makes the rest of the run noise.
            self._healths = [
                diagnosis.health(name, sweeps.get(name, [])) for name in self.wired
            ]
            if any(not h.ok for h in self._healths):
                self._finish()
                self.stop()
                return
        else:
            for listener in self.wired:
                self._readings.append(
                    diagnosis.read(
                        singer,
                        listener,
                        (self._floor or {}).get(listener, []),
                        sweeps.get(listener, []),
                    )
                )

        self._advance()

    def _settle(self, seconds):
        deadline = time() + seconds
        while time() < deadline and not self._stop_event.is_set():
            self._stop_event.wait(0.05)

    def _collect(self, label, seconds):
        """Sweep every wired ear for `seconds`, keeping each sweep whole.

        Whole sweeps rather than a running mean because `health()` wants
        to know whether two sweeps were ever different from each other -
        a reading that never changes is a reading that is not being
        taken, and an average hides exactly that.
        """
        collected = {name: [] for name in self.wired}
        deadline = time() + seconds
        while time() < deadline and not self._stop_event.is_set():
            everything = self.audio.read_all()
            for name in self.wired:
                collected[name].append(tuple(everything[name]))

        elapsed = time() - (self._start_time or time())
        for name in self.wired:
            values = diagnosis.mean_bands(collected[name])
            if values is None:
                continue
            self._file.write(
                f"{elapsed}, {label}, {name}, "
                + ", ".join(f"{value:.1f}" for value in values)
                + "\n"
            )
        return collected

    def _finish(self):
        self._steps = diagnosis.diagnose(self._healths, self._readings, self.wired)
        self._outcome = diagnosis.summarise(self._healths, self._readings, self.wired)

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        children = dict(self._manual)
        for name in self.wired:
            body = self._bodies[name]
            children[f"{name} speaker"] = body.speaker
            children[f"{name} microphone"] = body.microphone
        return self._with_scenarios(children)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        wired = self.wired
        leaf(
            "wired",
            ", ".join(f"{name} ({audio.describe(name)})" for name in wired) or "none",
        )
        for name in self.unknown_wired:
            leaf("not a body", f"{name!r} is in params but is not one of the five")

        if self._outcome is not None:
            leaf("outcome", self._outcome)
        if self._current is not None:
            leaf("now sounding", audio.describe(self._current))
        elif self._queue is not None and self._floor is None:
            leaf("now sounding", "nothing - reading the floor")

        for health in self._healths:
            leaf(f"{health.body} ear", health.verdict)

        for reading in self._readings:
            leaf(
                f"{reading.singer} -> {reading.listener}",
                f"{reading.verdict} (+{reading.rise:.0f})",
            )

        for number, step in enumerate(self._steps, start=1):
            leaf(f"next {number}", step)

        if self._last_read is not None:
            leaf("last sweep", self._last_read)

        return states
