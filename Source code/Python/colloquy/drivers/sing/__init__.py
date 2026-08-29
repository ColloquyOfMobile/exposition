# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/sing/__init__.py

"""A body sending a ten-bit pattern as sound, on the light channel's clock.

`male/search/blink/Blink` writes a ring; this writes a speaker, and it is
otherwise the same thread. That is not a convenience - it is TJ's design.
In his firmware a sound message *is* a light message: the same ten-bit
tables, the same 50 ms tick, the pattern in the on and the off rather
than in the pitch (CODE_DOCUMENTATION 9.2, 9.10). A body's pitch says
*who* is singing; the bits say *what*.

So the burst and the gap are the same shape as a male's ring, from
`colloquy/light_pattern_timing.py`, and for the same reason: the silence
frames the burst, so a window straddling it fails to match rather than
matching some rotation of the pattern.

**Unlike Blink, the pattern is given rather than looked up.** Blink asks
the male's drives what to say at the start of every burst. What a body
sings is decided by whoever started it - a female sings the male's own
pattern back to him, a male sings his `R`, and neither is a function of
how hungry he is at that instant.
"""
from time import time

from colloquy.base_thread import BaseThread
from colloquy.light_pattern_timing import (
    BIT_DURATION,
    BITS,
    BURST_DURATION,
    CYCLE_DURATION,
)
from colloquy.ui import leaves


class Sing(BaseThread):
    # Half of the answer; the scenario carries the whole exchange.
    scenario_names = ("an-answer-in-sound",)

    def __init__(self, owner):
        self._name = f"sing {owner.name}"
        super().__init__(owner=owner)
        self._cycle_start = 0
        self._bits = ()
        self._sounding = None
        self._pattern = ()

    @property
    def name(self):
        return self._name

    @property
    def body(self):
        return self.owner

    @property
    def pattern(self):
        """The ten bits this will send from the next burst on."""
        return self._pattern

    @pattern.setter
    def pattern(self, bits):
        self._pattern = tuple(bits)

    @property
    def bits(self):
        """The bits the *current* burst is sending, empty before the first."""
        return self._bits

    @property
    def is_transmitting(self):
        """True while the burst is sounding, False during the silence."""
        return self.is_started and (time() - self._cycle_start) < BURST_DURATION

    # --- the clock, exactly Blink's --------------------------------------

    def loop(self):
        elapsed = time() - self._cycle_start
        if elapsed >= CYCLE_DURATION:
            self._start_burst()
            return

        index = int(elapsed // BIT_DURATION)
        self._sound(self._bits[index] if index < BITS else 0)

    def _start_burst(self):
        self._cycle_start = time()
        # Read once per burst, like Blink: a pattern changed halfway
        # through would splice two messages into one nobody can read.
        self._bits = tuple(self._pattern)
        self._sound(self._bits[0] if self._bits else 0)

    def _sound(self, value):
        # Every speaker write is a serial round trip, and the thread ticks
        # far faster than a bit lasts - so only send what changes.
        if value == self._sounding:
            return
        if value:
            self.body.speaker.on()
        else:
            self.body.speaker.off()
        self._sounding = value

    def setup(self):
        # Zero rather than now, so the first loop() finds a whole cycle
        # elapsed and opens with a burst instead of a silence.
        self._cycle_start = 0
        self._bits = ()
        self._sounding = None

    def setdown(self):
        self.body.speaker.off()
        self._sounding = 0

    @property
    def snapshot_children(self):
        return self._with_scenarios({})

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        if not self.is_started:
            return states

        leaf = leaves.into(states, path)
        leaf("singing", "".join(str(bit) for bit in self._bits) or "nothing yet")
        leaf("speaker", "sounding" if self.is_transmitting else "silent (gap)")
        return states
