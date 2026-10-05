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
- **one board per body** - the second full solution, and the reason the
  two are kept side by side rather than one being folded into the other.
  Same fixed harness, five Arduino Pro Minis instead of one Mega, and the
  filters and analysers moved out of the rack and into the bodies. It
  ends by comparing itself with `next pcb` and saying which to build.
- **opencm and pro minis** - the third, **dropped 2026-09-30**: it put a
  single OpenCM 9.04 in place of the U2D2 and the bridge, and the OpenCM
  is discontinued. Kept as the record of why; the U2D2 stays.
- **ad9833 dual mode** - the fourth, and the one chosen for the voices:
  one set of boards that runs centrally (Mega, U2D2, this program) or
  distributed (a Pro Mini per body, the Mega bridging them, the U2D2 still
  on the servos; close to TJ's), changed by fitting the Pro Minis, moving
  jumpers and reflashing the Mega. The same AD9833 voice channel
  sits in the rack for one and in each body for the other.
- **thomas or teensy** - the fifth, and the one that tests rather than
  chooses: the v2 board with Thomas's chain kept whole and a Teensy 4.1
  chain (I2S DACs out, sampled microphones in) added beside it. One
  shunt moves five relays and the board is in one mode or the other,
  never both. Every connection to the harness is the v2 board's.
- **shields** - the sixth: the main board becomes a backplane with no
  silicon on it, and every solution is a set of shields in its slots -
  the U2D2, a computing shield (the Mega itself, or a Teensy 4.1 on an
  adapter in the Mega's footprint), the MSGEQ7 analyser shield (the
  Mega's ear; the Teensy takes the microphones directly) and five voice
  cards, the output filters, whose corner is four resistors. Its figures
  are computed by `shields.py`.
- **microphone board** - not a solution but a board: one per body,
  carrying the MAX9814 and screwed to the body's aluminium extrusion,
  in place of Thomas's breakout on its hand-wired carrier. Its figures
  are computed by `microphone_board.py`.
- **cad boards** - an index of every board designed in `CAD/`: what it
  is, where it sits, how many there are, and which document holds its
  pinouts. The only document here that covers the TPA2005D1 breakout and
  the v2 KiCad project.
- **sound options** - five ways to make the bodies' voices and hear them
  (TJ's, Thomas's, AD9833s, a Teensy 4.1, a USB sound card), compared on
  price, effort, board complexity and distance from TJ. About the sound
  channel alone, which the three solutions above take as given.

And beside them, generated rather than written:

- **harness** - the four small PCBs on the far side of the box's
  connectors (`center`, `female static`, `female base`, `male static`).
  Nothing but connectors and copper, and the thing all three documents
  above describe themselves against. Read out of their KiCad files every
  time it is opened, since a second copy of a pinout is a pinout that can
  be wrong.

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


class OneBoardPerBody(_ElectronicsDocument):
    """The second full solution, against the same fixed harness.

    A sibling of `next pcb` rather than a child of it: it is not a
    variation on that board, it is a different answer to the same
    question, and both are complete. Written rather than generated -
    it is a specification and the reasoning behind it, and there is no
    netlist behind it yet.
    """

    file_name = "ONE_BOARD_PER_BODY.md"
    document_name = "one board per body"


class OpenCMAndProMinis(_ElectronicsDocument):
    """Dropped 2026-09-30 (the OpenCM is discontinued); kept as a record.

    The third solution, and a sibling of the other two.

    Not a third architecture: it is `one board per body` with the rack
    tidied - the U2D2 and the bridge collapsed into one OpenCM, which is
    a controller where those two are an adapter and a relay. Everything
    about the bodies is that document's and is not repeated here.
    """

    file_name = "OPENCM_AND_PRO_MINIS.md"
    document_name = "opencm and pro minis"


class AD9833DualMode(_ElectronicsDocument):
    """The fourth solution, and a sibling of the other three.

    Built out of them rather than beside them: central mode is `next pcb`
    with its filter bank replaced by AD9833 voice channels, distributed
    mode is `one board per body` with the Mega as its bridge and the voice
    made the same way. No OpenCM: the U2D2 masters the servos in both.
    """

    file_name = "AD9833_DUAL_MODE.md"
    document_name = "ad9833 dual mode"


class ThomasOrTeensy(_ElectronicsDocument):
    """The fifth solution, and a sibling of the other four.

    Not a choice between the two sound chains but a board for trying
    both: Thomas mode is the v2 project as drawn, Teensy mode is the
    Teensy column of `sound options` made into a circuit, and a shunt
    picks one for the whole board. Its connector tables are held to the
    v2 project's `circuit.json` by `test_thomas_or_teensy.py`.
    """

    file_name = "THOMAS_OR_TEENSY.md"
    document_name = "thomas or teensy"


class Shields(_ElectronicsDocument):
    """The sixth solution, and a sibling of the other five.

    Not a board with the solutions on it but a backplane they plug into:
    the v2 board with its audio parts moved out into shields, so that
    trying another solution is changing one shield and holding the rest
    still. Its tables are held to the v2 project's `circuit.json`, to the
    sketch and to `shields.py` - which computes the voice cards' filter
    and the Teensy's frequencies - by `test_shields.py`.
    """

    file_name = "SHIELDS.md"
    document_name = "shields"


class MicrophoneBoard(_ElectronicsDocument):
    """One board per body: the microphone, on the extrusion.

    Beside the solutions rather than under one, since every one of them
    hears through it - the MSGEQ7s on the Mega and the Teensy's direct
    path alike. Its connector is held to the harness boards' microphone
    sockets, and its figures to `microphone_board.py`, by
    `test_microphone_board.py`.
    """

    file_name = "MICROPHONE_BOARD.md"
    document_name = "microphone board"


class CADBoards(_ElectronicsDocument):
    """An index of the design files, not a fifth copy of their pinouts:
    those stay in `harness` and `as built`, which read the copper."""

    file_name = "CAD_BOARDS.md"
    document_name = "cad boards"


class SoundOptions(_ElectronicsDocument):
    """A comparison, not a fourth solution: it is about the sound channel
    alone, and asks what should make the voices once the pitches no
    longer have to fit the analyser's bands."""

    file_name = "SOUND_OPTIONS.md"
    document_name = "sound options"


class NextPCB(_ElectronicsDocument):
    """The specification, and under it the three things generated from it.

    They hang here rather than beside it because that is what they are:
    `NEXT_PCB.md` is the reasoning and these are what it produces, so a
    reader who has not opened `next pcb` has no use for its netlist. As
    siblings they also had to carry its name at the front of each of
    theirs, which is a namespace spelled out three times in the one place
    the tree already provides one.
    """

    file_name = "NEXT_PCB.md"
    document_name = "next pcb"

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._generated = [
            GeneratedDocument(
                owner=self, document_name="netlist", source=_netlist,
                written_to=f"{_GENERATED_FOLDER}/NETLIST.md",
            ),
            GeneratedDocument(
                owner=self, document_name="bill of materials", source=_bom,
                written_to=f"{_GENERATED_FOLDER}/BOM.md",
            ),
            GeneratedDocument(
                owner=self, document_name="mechanical", source=_mechanical,
                written_to=f"{_GENERATED_FOLDER}/MECHANICAL.md",
            ),
        ]

    @property
    def generated(self):
        return list(self._generated)

    @property
    def snapshot_children(self):
        return {document.name: document for document in self._generated}


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


def _harness():
    from .harness import markdown

    return markdown()


class Electronics(Base):
    """The written documents, and the harness beside them.

    Five written: three that answer questions about the board in the rack
    and get confused the moment they share a page, and two more that are
    whole second and third answers to the third of those. What `next pcb` generates hangs under
    `next pcb` rather than beside it. The split between written and
    generated is visible on the page anyway, since a generated one has no
    `edit` - see `GeneratedDocument`.

    **`harness` is here rather than under any of them** because it is not
    about the board in the rack at all: it is the four small PCBs on the
    far side of its connectors, and all three of the others describe
    themselves against it. Generated for the usual reason - the pinouts
    are in four KiCad files, and a second copy of a pinout is a pinout
    that can be wrong.
    """

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._documents = [
            AsBuilt(owner=self),
            DirtyRework(owner=self),
            NextPCB(owner=self),
            OneBoardPerBody(owner=self),
            OpenCMAndProMinis(owner=self),
            AD9833DualMode(owner=self),
            ThomasOrTeensy(owner=self),
            Shields(owner=self),
            MicrophoneBoard(owner=self),
            SoundOptions(owner=self),
            CADBoards(owner=self),
        ]
        # Not written to disk: nothing generates a file for it, and the
        # KiCad projects it reads are the copy anybody would want open.
        self._harness = GeneratedDocument(
            owner=self, document_name="harness", source=_harness,
        )

    @property
    def name(self):
        return "electronics"

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def documents(self):
        """The written ones. `harness` is not among them - it has no file
        to edit and no `edit` to offer."""
        return list(self._documents)

    @property
    def harness(self):
        return self._harness

    @property
    def snapshot_children(self):
        children = {document.name: document for document in self._documents}
        children[self._harness.name] = self._harness
        return children
