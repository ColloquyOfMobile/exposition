# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/electronics/__init__.py

"""The electronics box: what is in it, what to change, what to build next.

Three documents, and the split is deliberate. They answer three questions
that get confused with each other the moment they share a page:

- **as built** - what the board in the rack does *now*. Every net, every
  connector, every Mega pin. Read off the KiCad files rather than
  remembered, and it is the only one of the three that is a statement of
  fact rather than of intent.
- **dirty rework** - the cuts and the jumpers that put Thomas's audio
  subsystem into that board without waiting for a new one. This is the
  one somebody stands over with a scalpel.
- **next PCB** - what the board that replaces it should do, with the
  rework's findings folded in. It exists so that the dirty version is a
  prototype of something rather than a detour.

**Why here and not under `drivers`.** The 2026-08-21 rename drew the line
and this is on the far side of it: a servo's goal position would not be
true with the software switched off, and which pin a track lands on
would. See `hardware/__init__.py`.

**Not gated by `is_simulated`.** The machine with the board actually in it
is the one place none of this is hypothetical - and the machine somebody
is holding a scalpel over is likely to be the other one. Both want it.
"""
from pathlib import Path

from colloquy.base import Base
from colloquy.markdown_document import MarkdownDocument

_FOLDER = Path(__file__).resolve().parent


class _ElectronicsDocument(MarkdownDocument):
    """Shared only so that the three below are one line each."""

    folder = _FOLDER


class AsBuilt(_ElectronicsDocument):
    file_name = "AS_BUILT.md"
    document_name = "as built"


class DirtyRework(_ElectronicsDocument):
    file_name = "DIRTY_REWORK.md"
    document_name = "dirty rework"


class NextPCB(_ElectronicsDocument):
    file_name = "NEXT_PCB.md"
    document_name = "next pcb"


class Electronics(Base):
    """The three documents, in the order they are wanted."""

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._documents = [
            AsBuilt(owner=self),
            DirtyRework(owner=self),
            NextPCB(owner=self),
        ]

    @property
    def name(self):
        return "electronics"

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def documents(self):
        return list(self._documents)

    @property
    def snapshot_children(self):
        return {document.name: document for document in self._documents}
