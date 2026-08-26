# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/speaker/__init__.py

"""One body's voice: on, off, and nothing else.

There is deliberately no pitch here. A body's pitch is decided by which
hardware timer drives its pin, which is decided by the board, so asking
for one would be asking for something the firmware cannot give - see
`drivers/audio.py`. What Python controls is whether the tone is sounding.

That is also all the sound channel ever needed. In TJ's firmware a sound
message is the *same* message as a light message - same ten-bit tables,
same clock - and the pattern is in the on and the off, not in the pitch
(CODE_DOCUMENTATION 9.2, 9.10). So a `Sing` thread mirroring
`drivers/male/search/blink/Blink` can be written straight on top of this:
where Blink writes a ring, Sing writes a speaker.

Nothing writes to it that way yet. This is the layer under that.
"""
from pathlib import Path

from colloquy.base import Base
from colloquy.ui import leaves

from .. import audio


class Speaker(Base):
    """The tone one body can make, as a node on the page."""

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._is_singing = False
        self["on"] = self.on
        self["off"] = self.off

    @property
    def name(self):
        return "speaker"

    @property
    def body(self):
        return self.owner

    @property
    def arduino(self):
        return self.owner.arduino

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def params(self):
        return self.owner.params

    @property
    def arduino_path(self):
        """`f1/speaker`, `m2/speaker` - the body's own short prefix, the
        same one its light sensor and its pixel groups use."""
        return Path(f"{self.body.name[0]}{self.body.id_number}/speaker")

    @property
    def voice(self):
        return audio.VOICES[self.body.name]

    @property
    def hz(self):
        return self.voice["hz"]

    @property
    def is_singing(self):
        """What was last asked for, not what is actually sounding.

        The firmware answers every set with the state it is now in, and
        that answer is what is kept here - so this is a report of the last
        exchange rather than a guess. It still cannot know about a board
        that rebooted underneath it, which is what `off()` at startup and
        at shutdown is for.
        """
        return self._is_singing

    # --- the two things it does -------------------------------------------

    def on(self, request=None):
        return self._set(True)

    def off(self, request=None):
        return self._set(False)

    def _set(self, singing):
        with self.arduino:
            response = self.arduino.send(self.arduino_path, on=1 if singing else 0)
        self._is_singing = response.strip() == b"1"
        return self._is_singing

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        return {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        leaf("state", "sounding" if self._is_singing else "silent")
        # Both of these are here for somebody holding a scope probe: when
        # a body turns out to be mute, the first question is which pin.
        leaf("voice", audio.describe(self.body.name))
        return states
