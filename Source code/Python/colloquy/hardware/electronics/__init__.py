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
from colloquy.markdown_document import GeneratedDocument, MarkdownDocument

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


# The three generated ones, and where `py next_pcb.py` also writes them.
# Imported inside the callables rather than at module scope: the mechanical
# one parses a 1.7 MB board file, and nothing should pay for that at
# startup on the chance somebody opens the node.
_GENERATED_FOLDER = "CAD/KiCad/electronic box v2"


def _netlist():
    from .next_pcb_report import netlist_markdown

    return netlist_markdown()


def _bom():
    from .next_pcb_report import bom_markdown

    return bom_markdown()


def _mechanical():
    from .next_pcb_report import mechanical_markdown

    return mechanical_markdown()


class Electronics(Base):
    """The documents, in the order they are wanted.

    Three written and three generated, and the split is visible on the
    page: the generated ones have no `edit`. See `GeneratedDocument` -
    they are rendered from the generator on every view rather than from
    the file it also writes, so the page cannot show a stale copy of a
    design that has moved.
    """

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._documents = [
            AsBuilt(owner=self),
            DirtyRework(owner=self),
            NextPCB(owner=self),
            GeneratedDocument(
                owner=self, document_name="next pcb netlist",
                source=_netlist,
                written_to=f"{_GENERATED_FOLDER}/NETLIST.md",
            ),
            GeneratedDocument(
                owner=self, document_name="next pcb bill of materials",
                source=_bom,
                written_to=f"{_GENERATED_FOLDER}/BOM.md",
            ),
            GeneratedDocument(
                owner=self, document_name="next pcb mechanical",
                source=_mechanical,
                written_to=f"{_GENERATED_FOLDER}/MECHANICAL.md",
            ),
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
