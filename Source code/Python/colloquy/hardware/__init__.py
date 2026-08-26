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

Two things so far, and they are two rather than one on purpose:

- `main_pcb` is a **state** - is the board in the rack, and the command
  to take it out safely. It is deliberately its own section rather than a
  child of `drivers/arduino` or `drivers/u2d2`, because it is neither and
  both: one board carries both links, so unmounting it takes out the
  Arduino and the U2D2 together and neither of them owns it.
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


class Hardware(Base):
    """What is physically in the installation, on the page."""

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._main_pcb = MainPCB(owner=self)
        self[self._main_pcb.name] = self._main_pcb
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
    def electronics(self):
        return self._electronics

    @property
    def snapshot_children(self):
        return {
            self._main_pcb.name: self._main_pcb,
            self._electronics.name: self._electronics,
        }
