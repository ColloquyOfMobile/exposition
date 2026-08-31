# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/__init__.py

"""The physical installation: the things you can put a hand on.

Distinct from `drivers/`, and the distinction is the one the rename of
2026-08-21 drew rather than one it blurred. `drivers` is the layer that
*drives* the piece - servos, the bus, the bodies, the behaviours. This is
about the equipment itself: which boards are in the rack, whether they
are wired up, what has to happen before a cable comes off. The word
"hardware" was always still right for that, and this is where it belongs.

The test for what goes here: would it still be true with the software
switched off? A servo's goal position would not. Whether the main PCB is
screwed into the installation would.

Three things so far, and they are three rather than one on purpose:

- `main_pcb` is a **state** - is the board in the rack, and the command
  to take it out safely. It is deliberately its own section rather than a
  child of `drivers/arduino` or `drivers/u2d2`, because it is neither and
  both: one board carries both links, so unmounting it takes out the
  Arduino and the U2D2 together and neither of them owns it.
- `motors` is the other **state** - is the Dynamixel chain plugged in,
  and the command to take it off without any servo losing the turn count
  that lives in its volatile memory. Separate from `main_pcb` because the
  two cables come off independently and for different reasons: the board
  goes to a desk to be debugged, and the chain comes off when something
  else wants the U2D2's 12 V. It is also the one of the three that
  deliberately leaves the server running afterwards.
- `electronics` is the **description** - three documents saying what that
  board does now, what to cut and jumper to put the audio subsystem into
  it, and what the board that replaces it should be. Nothing there is a
  reading or a command; it is what somebody standing over the rack with a
  scalpel needs to know, which is exactly the sort of thing that
  otherwise lives in a PDF nobody at the rack has open.
"""
from colloquy.base import Base

from .electronics import Electronics
from .main_pcb import MainPCB
from .motors import Motors


class Hardware(Base):
    """What is physically in the installation, on the page."""

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._main_pcb = MainPCB(owner=self)
        self[self._main_pcb.name] = self._main_pcb
        self._motors = Motors(owner=self)
        self[self._motors.name] = self._motors
        self._electronics = Electronics(owner=self)
        self[self._electronics.name] = self._electronics

    @property
    def name(self):
        return "hardware"

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def main_pcb(self):
        return self._main_pcb

    @property
    def motors(self):
        return self._motors

    @property
    def electronics(self):
        return self._electronics

    @property
    def snapshot_children(self):
        return {
            self._main_pcb.name: self._main_pcb,
            self._motors.name: self._motors,
            self._electronics.name: self._electronics,
        }
