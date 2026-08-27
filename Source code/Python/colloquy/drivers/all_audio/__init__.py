# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/all_audio/__init__.py

"""Every voice and every ear at once, which is not just a convenience.

`AllNeopixels` exists to save writing a loop. This exists because the
loop would be *wrong*:

- **Every ear is read in one sweep or none.** The five analyser modules
  share one strobe line, so the firmware walks the seven bands once and
  all five modules answer at every step. Reading five microphones one at
  a time takes five times as long *and* takes place at five different
  moments, which is exactly what you must not do when comparing what two
  bodies heard of the same sound.
- **Silence is one command.** A shutdown, an emergency stop and a failed
  test run all want every tone off, and none of them is in a position to
  send five commands and check five replies. The firmware has its own
  `speakers/off` for the same reason.
"""
from pathlib import Path

from colloquy.base import Base
from colloquy.ui import leaves

from .. import audio

_READ_ALL = Path("microphones")
_SILENCE = Path("speakers/off")


class AllAudio(Base):
    """The sound half of the installation, addressed as one thing."""

    def __init__(self, owner, bodies):
        super().__init__(owner=owner)
        self._bodies = {body.name: body for body in bodies}
        self._last = None
        self["read every microphone"] = self.read_all_command
        self["silence every speaker"] = self.silence_command

    @property
    def name(self):
        return "all audio"

    @property
    def arduino(self):
        return self.owner.arduino

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def speakers(self):
        return [body.speaker for body in self._bodies.values()]

    @property
    def microphones(self):
        return [body.microphone for body in self._bodies.values()]

    # --- hearing ----------------------------------------------------------

    def read_all(self):
        """One sweep: `{body name: (seven band values)}` for all five.

        The firmware answers thirty-five numbers, module-major, in body
        order - so the split below is the *only* place that order is
        assumed, and `audio.BODIES` is where it is written down.
        """
        with self.arduino:
            response = self.arduino.send(_READ_ALL)

        values = [int(token) for token in response.split()]
        width = len(audio.BANDS_HZ)
        expected = width * len(audio.BODIES)
        if len(values) != expected:
            raise ValueError(
                f"'microphones' answered {len(values)} numbers, expected "
                f"{expected}: {response!r}"
            )

        readings = {}
        for index, name in enumerate(audio.BODIES):
            readings[name] = tuple(values[index * width : (index + 1) * width])
            # Each body's own node keeps what it heard, so opening one
            # microphone on the page shows the sweep it took part in
            # rather than nothing until it is read on its own.
            self._bodies[name].microphone._last = readings[name]

        self._last = readings
        return readings

    def read_all_command(self, request=None):
        return self.read_all()

    # --- silence ----------------------------------------------------------

    def silence(self):
        """Every tone off, in one command."""
        with self.arduino:
            self.arduino.send(_SILENCE)
        for speaker in self.speakers:
            speaker._is_singing = False

    def silence_command(self, request=None):
        self.silence()
        return "every speaker is silent"

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        return {
            "read every microphone": self.read_all_command,
            "silence every speaker": self.silence_command,
        }

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        sounding = [
            f"{speaker.body.name} ({speaker.hz} Hz)"
            for speaker in self.speakers
            if speaker.is_singing
        ]
        leaf("sounding", ", ".join(sounding) if sounding else "nothing")

        if self._last is None:
            leaf("last sweep", "not read yet")
            return states

        for name in audio.BODIES:
            leaf(name, " ".join(str(value) for value in self._last[name]))
        leaf("bands", " ".join(f"{hz}Hz" for hz in audio.BANDS_HZ))
        return states
