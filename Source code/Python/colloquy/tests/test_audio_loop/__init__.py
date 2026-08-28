# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_audio_loop/__init__.py

"""Does each body's voice come back into each body's ear?

The same question `test_audio_subsystem` asks, on the other board. That
one drives **Thomas's** Mega over **his** tester firmware's serial menu,
at a bench, with his five speakers and his five microphones on the desk
beside it. This one drives the **installation's own** Arduino over the
JSON link every other command in this repo uses, with the speakers and
microphones that are in the bodies.

Both are worth having, and the difference is not redundancy:

- His answers *is the audio hardware any good*. It is the acceptance test
  for five boards, and it can be run in an office with the piece nowhere
  near.
- This one answers *is the audio hardware wired into the installation
  correctly*. It is the only one that can catch a body singing down
  another body's channel, because it is the only one that knows which
  body is which - his board cannot, and his own setup document says so
  in as many words.

**What it does to the room.** Five tones, three seconds each, ascending,
with silence between - about half a minute of the installation humming to
itself. Nothing moves and nothing lights up. It is safe to run in front
of visitors and it will not be quiet.

**A failure names a pair, not a link.** "2500 Hz on male2's microphone:
silent" is a whole chain having failed at once - timer, pin, filter,
amplifier, speaker, air, microphone, MSGEQ7, ADC - and this test cannot
say which. The manual commands beside it are for that: hold one tone on
and walk the room with an ear.
"""
from datetime import datetime
from functools import partial
from time import time

from colloquy.base_thread import BaseThread
from colloquy.drivers import audio
from colloquy.ui import leaves

from . import verdicts


class TestAudioLoop(BaseThread):
    scenario_names = ("audio-loop-test",)

    # How long each tone is held. Long enough for somebody to hear it and
    # to place it in the room, since this is meant to be listened to.
    TONE_SECONDS = 3.0

    # After a tone changes, before its readings count. The MSGEQ7 is a
    # peak detector with its own decay, so the first sweep after a change
    # still carries the last one. The firmware already throws away ten
    # sweeps per read for the same reason; this is the slower half of it.
    SETTLE_SECONDS = 0.7

    # How far a band has to rise above its own silent level to count as
    # heard. Off the ADC the range is 0-1023 and a tone in its own band is
    # not subtle, so this is deliberately blunt: it is here to reject
    # drift and room noise, not to measure anything. A real room may want
    # it moved, which is why it is on the page.
    MARGIN = 60

    def __init__(self, owner, result_folder):
        super().__init__(owner=owner)

        self._bodies = {body.name: body for body in self.drivers.bodies}

        # For chasing a failure once the sweep has said there is one. Each
        # holds a tone on until something else turns it off, which is what
        # you want while walking the room.
        # All five, not just the wired ones, and on purpose: holding an
        # unwired body's tone is how you put a scope on its pin *before*
        # its amplifier exists. It makes no sound, which is the point.
        self._manual = {}
        for name in audio.BODIES_BY_PITCH:
            voice = audio.VOICES[name]
            label = f"hold {name} on ({voice['hz']} Hz, {voice['pin']})"
            self._manual[label] = partial(self._hold, name)
        self._manual["silence"] = self._silence
        self._manual["all five at once"] = self._all_at_once

        self._dir_path = result_folder / self.name
        if not self._dir_path.exists():
            self._dir_path.mkdir()

        self._file = None
        self._start_time = None
        self._queue = None
        self._current = None
        self._silence_floor = None
        self._verdicts = {}
        self._outcome = None

    @property
    def name(self):
        return "test audio loop"

    @property
    def audio(self):
        return self.drivers.audio

    @property
    def wired(self):
        """The bodies whose audio channel is actually built.

        The grid is 5x5 only when the hardware is. An unwired analyser
        input is a floating ADC pin, and a floating pin does not read
        silence - so a full sweep on a part-built board reports a wall of
        fictional failures with the real answers buried in it. Read from
        params on every use, the same list `test audio bringup` reads.
        """
        chosen = list(self.colloquy.params["audio"]["wired bodies"])
        return [name for name in audio.BODIES_BY_PITCH if name in chosen]

    # --- the manual commands ----------------------------------------------

    def _hold(self, name, request=None):
        """One voice on, the others off. Not additive on purpose: the
        question these commands answer is 'where is *that* tone coming
        from', and four other tones in the room is not the way to ask."""
        self.audio.silence()
        self._bodies[name].speaker.on()
        return f"{name} is sounding at {audio.VOICES[name]['hz']} Hz"

    def _silence(self, request=None):
        self.audio.silence()
        return "everything is quiet"

    def _all_at_once(self, request=None):
        for name in self.wired:
            self._bodies[name].speaker.on()
        return (
            f"{len(self.wired)} sounding at once - every wired band should "
            "rise on every wired module"
        )

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
        self._verdicts = {}
        self._silence_floor = None
        self._outcome = None
        self._file.write(
            "seconds, sounding, listener, "
            + ", ".join(f"{hz} Hz" for hz in audio.BANDS_HZ)
            + "\n"
        )
        # Silence first, always. A run that begins with something already
        # sounding measures its floor against that tone and then reports
        # every other body as silent - which reads as five broken
        # speakers rather than as one that was left on.
        self.audio.silence()
        self._queue = [None] + list(self.wired)
        self._advance()

    def setdown(self):
        self._start_time = None
        self._current = None
        # Never raising, and the file closed either way. This was a bare
        # `self.audio.silence()`, so a link that dropped during the run
        # took the whole teardown with it: the tone stayed on, the CSV
        # was left open, and BaseThread._run_in_context never reached the
        # stop() after its setdown(). A dropped link is exactly when this
        # happens - see hardware > electronics > dirty rework, section 0,
        # on the 5 V - and it is the moment a body is most likely to be
        # left humming at somebody. Colloquy.silence_speakers is the one
        # that swallows, for this reason.
        try:
            self.colloquy.silence_speakers()
        finally:
            if self._file is not None:
                self._file.close()

    def _advance(self):
        if not self._queue:
            self._current = None
            self._outcome = verdicts.summarise(self._verdicts)
            self.stop()
            return
        self._current = self._queue.pop(0)

    def loop(self):
        if self._current is None and self._queue is None:
            return

        singer = self._current
        label = "silence" if singer is None else singer

        self.audio.silence()
        if singer is not None:
            self._bodies[singer].speaker.on()

        self._settle(self.SETTLE_SECONDS)
        readings = self._collect(label)

        if singer is None:
            self._silence_floor = readings
        else:
            self._judge(singer, readings)

        self._advance()

    def _settle(self, seconds):
        deadline = time() + seconds
        while time() < deadline and not self._stop_event.is_set():
            self._stop_event.wait(0.05)

    def _collect(self, label):
        """Sweep every ear for TONE_SECONDS and average what came back.

        Averaged rather than sampled once because the MSGEQ7's internal
        scan is fast enough to catch individual points on the waveform of
        the two lowest tones, so one reading of a steady 160 Hz varies
        with where in the cycle it landed. Averaging is enough to say
        "heard"; it is not how to sample a tone, and whatever eventually
        decodes a pattern will have to do it Thomas's way instead - four
        reads in quick succession at 160 Hz, two at 400.
        """
        totals = {name: [0] * len(audio.BANDS_HZ) for name in self.wired}
        sweeps = 0

        deadline = time() + self.TONE_SECONDS
        while time() < deadline and not self._stop_event.is_set():
            everything = self.audio.read_all()
            for name in self.wired:
                for index, value in enumerate(everything[name]):
                    totals[name][index] += value
            sweeps += 1

        if not sweeps:
            return {}

        elapsed = time() - self._start_time
        averages = {}
        for name in self.wired:
            averages[name] = tuple(total / sweeps for total in totals[name])
            self._file.write(
                f"{elapsed}, {label}, {name}, "
                + ", ".join(f"{value:.1f}" for value in averages[name])
                + "\n"
            )
        return averages

    def _judge(self, singer, readings):
        for listener in self.wired:
            floor = (self._silence_floor or {}).get(listener)
            heard = readings.get(listener)
            self._verdicts[(singer, listener)] = verdicts.verdict(
                floor, heard, singer, self.MARGIN
            )

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

        # Which board this is talking to, said before anything it goes on
        # to say about it. The stand-in answers a sweep with plausible
        # numbers, so a whole run against it comes out clean and reads
        # exactly like a good one. Told by the lead rather than by the
        # machine: the bench is `is_simulated` and the board is on the end
        # of a USB lead all the same - see `Arduino.is_using_the_stand_in`.
        leaf(
            "board",
            "the stand-in - nothing below was measured"
            if self.drivers.arduino.is_using_the_stand_in
            else f"a real board on {self.drivers.arduino.port_name}",
        )

        if self._outcome is not None:
            leaf("outcome", self._outcome)
        if self._current is not None:
            leaf("now sounding", audio.describe(self._current))
        elif self._queue is not None and self._silence_floor is None:
            leaf("now sounding", "nothing - reading the floor")

        for (singer, listener), value in sorted(self._verdicts.items()):
            leaf(f"{singer} -> {listener}", value)

        return states
