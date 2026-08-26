# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/microphone/__init__.py

"""One body's ear: seven numbers, one per analyser band.

Behind it is a MAX9814 microphone module in the body and one of five
MSGEQ7 analysers in the box. What comes back is not a sound level - it is
how much energy the chip found in each of seven fixed bands, 0-1023 off
the ADC.

**Reading one body costs what reading five costs.** The five modules share
one strobe line, so the firmware walks the seven bands once and every
module answers at every step. Anything that wants more than one body
should ask `Microphones.read_all()` on the Arduino rather than five of
these in a row: five separate reads take five times as long and, worse,
take place at five different moments, which is the one thing you do not
want when comparing bodies to each other.

**One property to know before deciding anything on a single reading.** The
MSGEQ7's internal scan is fast enough to catch individual points on the
*waveform* of the 160 Hz and 400 Hz signals, so repeated readings of a
steady tone vary depending on where in the cycle the chip happened to
sample. Thomas's remedy is to read four times in quick succession when
expecting 160 Hz and twice for 400 Hz, and take the best - in his tests
160 Hz always gave at least two high hits out of four. `read_band` does
not do that; `TestAudioLoop` averages whole sweeps instead, which is
enough to say "heard" and is not how to sample a tone. Whatever eventually
decodes a pattern out of this will have to.
"""
from pathlib import Path

from colloquy.base import Base
from colloquy.ui import leaves

from .. import audio


class Microphone(Base):
    """What one body hears, band by band."""

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._last = None
        self["read"] = self.read_command

    @property
    def name(self):
        return "microphone"

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
        return Path(f"{self.body.name[0]}{self.body.id_number}/microphone")

    @property
    def module(self):
        """Which of the five analyser modules is this body's ear."""
        return audio.module_of(self.body.name)

    @property
    def own_band(self):
        """The band this body's *own* voice sits in - which is the one it
        should never hear itself in, since nobody listens while they
        speak (CODE_DOCUMENTATION 9.12)."""
        return audio.band_of_body(self.body.name)

    # --- reading ----------------------------------------------------------

    def read(self):
        """This body's seven bands, as a tuple of ints."""
        with self.arduino:
            response = self.arduino.send(self.arduino_path)
        values = tuple(int(token) for token in response.split())
        if len(values) != len(audio.BANDS_HZ):
            raise ValueError(
                f"{self.arduino_path} answered {len(values)} numbers, "
                f"expected {len(audio.BANDS_HZ)}: {response!r}"
            )
        self._last = values
        return values

    def read_command(self, request=None):
        return self.read()

    def read_band(self, index):
        return self.read()[index]

    def hears(self, hz, threshold):
        """Is there a tone of this pitch in what this ear is hearing?

        Blunt on purpose, and the threshold is the caller's: an absolute
        level is already the weakest part of the light side (8.2) and a
        microphone in a gallery full of visitors is worse. Nothing in the
        installation calls this yet - it is here so that the thing which
        eventually does has one place to be fixed.
        """
        return self.read()[audio.band_of(hz)] > threshold

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        return {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        leaf("module", f"{self.module} (A{self.module})")
        if self._last is None:
            leaf("bands", "not read yet")
            return states

        for hz, value in zip(audio.BANDS_HZ, self._last):
            label = f"{hz} Hz"
            if hz == audio.VOICES[self.body.name]["hz"]:
                # Marked because it is the one reading that means
                # something different: this body's own voice coming back
                # into its own ear is a wiring fault, not a message.
                label += " (own voice)"
            leaf(label, value)
        return states
