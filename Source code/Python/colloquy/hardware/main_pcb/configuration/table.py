# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/main_pcb/configuration/table.py

"""Every board the rack can hold, what each takes in its slots, and what
the page has been told is in there.

**Nothing in the hardware can say which of these is fitted.** `shields`
puts it outright - "there is no shield identification in hardware: the
silkscreen does that job" - and the same is true of every board here: a
Mega in the computing slot and a Teensy on its adapter look identical to
anything this program can ask before it has opened a port, and a voice
card announces nothing at all. So the configuration is a **record**,
written by a press, exactly as `main pcb`'s mounted flag is, and nothing
here pretends to have measured it.

Pure: a params entry in, readings and sentences out, and a new params
entry back. The node (`__init__.py`) is the only thing that touches the
tree or the file. Every value read from params is read defensively,
because params.json is hand-editable and a bad value has to arrive as a
sentence on the page - a render that raises emergency-stops the
installation.

Every sentence is the documents' own: what each board is comes from
`cad boards`, what each slot takes and what follows from it from
`shields` and `thomas or teensy`. Nothing here is a fact those documents
do not state.
"""
from collections.abc import Mapping, Sequence
from typing import Final, NamedTuple

from colloquy.drivers.audio import BODIES


class Choice(NamedTuple):
    """One thing a slot can hold.

    `name` is both the press on the page and the string params.json
    stores, so the record and the button can never drift apart.
    """

    name: str
    says: str


class Slot(NamedTuple):
    """A place something is plugged in, and what may be plugged into it."""

    name: str
    choices: tuple[Choice, ...]
    # What the document's first step fits - what an unrecorded slot is
    # taken to hold, and said to be taken to hold.
    default: str

    def choice(self, name: str) -> Choice | None:
        for choice in self.choices:
            if choice.name == name:
                return choice
        return None


class Board(NamedTuple):
    name: str
    says: str
    # Names of documents under `hardware > electronics`.
    documents: tuple[str, ...]
    slots: tuple[Slot, ...]
    # How its slots are changed, in its own document's words. Empty for a
    # board with nothing on it to change.
    changing: str


EMPTY: Final = "empty"

# --- shields -------------------------------------------------------------

MEGA: Final = "Mega 2560"
TEENSY_ADAPTER: Final = "Teensy 4.1 adapter"
MSGEQ7_CARRIER: Final = "MSGEQ7 carrier"
THOMAS_CARD: Final = "Thomas card"
REVALUED_CARD: Final = "re-valued card"

COMPUTING_SLOT: Final = Slot(
    "computing slot",
    (
        Choice(
            MEGA,
            "the Mega itself, upside down on the DSUB face, on its own USB "
            "lead: firmware 4, unmodified",
        ),
        Choice(
            TEENSY_ADAPTER,
            "a Teensy 4.1 on an adapter in the Mega's footprint: firmware 5, "
            "3.3 V behind translators",
        ),
        Choice(EMPTY, "nothing to drive a tone, a light or a sensor"),
    ),
    MEGA,
)

ANALYSER_SLOT: Final = Slot(
    "analyser slot",
    (
        Choice(
            MSGEQ7_CARRIER,
            "Thomas's five DFRobot MSGEQ7 modules on their carrier in JA1: "
            "the Mega's ear",
        ),
        Choice(
            EMPTY,
            "JA1 empty, as it is with the Teensy, which reads the microphones "
            "directly",
        ),
    ),
    MSGEQ7_CARRIER,
)


def _voice_slot(number: int, body: str) -> Slot:
    # Slot N is body N, in body order (`shields` section 2d), which is
    # module order - so the slot's name carries both and one number
    # identifies a body all the way round, as on every board so far.
    return Slot(
        f"JV{number} {body}",
        (
            Choice(THOMAS_CARD, f"Thomas's RC filter, with his values for {body}"),
            Choice(
                REVALUED_CARD,
                "Thomas's circuit valued for another pitch by R x C = 0.179 / f "
                "(`shields` section 5b); the pitch is in its silkscreen box",
            ),
            Choice(EMPTY, f"nothing reaches {body}'s line out: {body} makes no sound"),
        ),
        THOMAS_CARD,
    )


VOICE_SLOTS: Final = tuple(
    _voice_slot(number, body) for number, body in enumerate(BODIES, start=1)
)
# Slot name -> the body it speaks for.
BODY_OF: Final = {slot.name: body for slot, body in zip(VOICE_SLOTS, BODIES)}
_VOICE_RANGE: Final = f"JV1-JV{len(VOICE_SLOTS)}"

# --- thomas or teensy ----------------------------------------------------

# The shunt's two positions, spelled as the silkscreen spells them.
THOMAS: Final = "THOMAS"
TEENSY: Final = "TEENSY"
TEENSY_41: Final = "Teensy 4.1"

MODE_SHUNT: Final = Slot(
    "mode shunt",
    (
        Choice(
            THOMAS,
            "relays released: Thomas's chain reaches every body, firmware 4 "
            "as it is",
        ),
        Choice(
            TEENSY,
            "relays pulled in: the Teensy's voices reach every body and the "
            "Mega's tones reach nobody",
        ),
    ),
    THOMAS,
)

TEENSY_SOCKET: Final = Slot(
    "teensy socket",
    (
        Choice(TEENSY_41, "fitted, on its own USB lead"),
        Choice(
            EMPTY,
            "with the shunt on THOMAS the board is the v2 project electrically",
        ),
    ),
    EMPTY,
)

# --- the boards ----------------------------------------------------------

ELECTRONIC_BOX: Final = Board(
    "electronic box",
    "the board in service: the Mega 2560 underneath and the U2D2 on it, "
    "reworked by hand to carry Thomas's audio chain",
    ("as built", "dirty rework"),
    (),
    "",
)

CONTROL_V2: Final = Board(
    "colloquy control v2",
    "the v2 project: Thomas's chain on the board itself, the Mega and the "
    "U2D2 as on the electronic box",
    ("next pcb",),
    (),
    "",
)

THOMAS_OR_TEENSY: Final = Board(
    "thomas or teensy",
    "the v2 board with a Teensy 4.1 chain beside Thomas's; one shunt picks "
    "which of the two reaches the bodies",
    ("thomas or teensy",),
    (MODE_SHUNT, TEENSY_SOCKET),
    "stop the piece from the page; fit or pull the Teensy only with the "
    "board powered down; then move the shunt (`thomas or teensy` section 9)",
)

SHIELDS_BACKPLANE: Final = Board(
    "shields backplane",
    "the v2 board as a backplane with no solution of its own: a computing "
    "shield, the analyser carrier and five voice cards plug into it",
    ("shields",),
    (COMPUTING_SLOT, ANALYSER_SLOT, *VOICE_SLOTS),
    "stop the piece from the page, unplug the rack supply and the computing "
    "USB, change the shield, write it in its silkscreen box, and power both "
    "back up together (`shields` section 10)",
)

BOARDS: Final = (ELECTRONIC_BOX, CONTROL_V2, THOMAS_OR_TEENSY, SHIELDS_BACKPLANE)


class Step(NamedTuple):
    """A whole configuration the shields document builds towards.

    `shields` section 0 orders them, and each changes as little as it can
    from the one before, so naming the step a record matches says more
    than its seven slots do.
    """

    name: str
    says: str
    fitted: dict[str, str]


def _step(computing: str, analyser: str) -> dict[str, str]:
    fitted = {COMPUTING_SLOT.name: computing, ANALYSER_SLOT.name: analyser}
    fitted.update({slot.name: THOMAS_CARD for slot in VOICE_SLOTS})
    return fitted


# `shields` section 0's two steps, in its words. The voice cards are
# Thomas's in both: step 2 plays the Mega's pitches on the Teensy, and
# re-valuing a card is the step after it.
SHIELD_STEPS: Final = (
    Step(
        "step 1: the Mega",
        "the v2 board electrically, firmware 4 unmodified - the exhibition "
        "depends on this step alone",
        _step(MEGA, MSGEQ7_CARRIER),
    ),
    Step(
        "step 2: the Teensy",
        "the same voices on the Teensy, and the microphones on the laptop",
        _step(TEENSY_ADAPTER, EMPTY),
    ),
)


def step_of(reading: "Reading") -> Step | None:
    """The documented step a record is, if it is one."""
    if reading.board is not SHIELDS_BACKPLANE:
        return None
    for step in SHIELD_STEPS:
        if step.fitted == reading.fitted:
            return step
    return None

# The one in the rack today. A fresh params.json says this, and so does
# one written before the configuration was recorded at all.
DEFAULT_BOARD: Final = ELECTRONIC_BOX.name

# The rack is a slot too - it takes a board - so the page draws the choice
# of board exactly as it draws the choice of a shield.
RACK: Final = Slot("board", tuple(Choice(b.name, b.says) for b in BOARDS), DEFAULT_BOARD)


def board_named(name: str) -> Board | None:
    for board in BOARDS:
        if board.name == name:
            return board
    return None


# --- reading the record --------------------------------------------------


class Reading(NamedTuple):
    # As stored, which may name no board at all.
    board_name: str
    board: Board | None
    # Slot name -> what it holds, for this board's slots only. A slot
    # nobody has recorded reads as its default; a value that is not one
    # of the slot's choices is kept as it was, so the page can say so.
    fitted: dict[str, str]
    # "" when nobody has ever pressed anything.
    recorded_at: str


def _as_dict(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def read(stored: object) -> Reading:
    """What `params["main pcb"]["configuration"]` says, whatever shape it
    is in."""
    entry = _as_dict(stored)
    board_name = str(entry.get("board", DEFAULT_BOARD))
    return Reading(
        board_name,
        board_named(board_name),
        fitted_on(stored, board_name),
        str(entry.get("recorded at", "")),
    )


def fitted_on(stored: object, board_name: str) -> dict[str, str]:
    """What is in each slot of one board, whether or not it is the board
    in the rack - a board taken out keeps its shields."""
    board = board_named(board_name)
    mine = _as_dict(_as_dict(_as_dict(stored).get("fitted")).get(board_name))
    return {
        slot.name: str(mine.get(slot.name, slot.default))
        for slot in (board.slots if board else ())
    }


# --- writing it ----------------------------------------------------------


def _copy(stored: object) -> dict[str, object]:
    """A plain, well-formed copy to write back whole.

    Whole, because only assignment saves params.json - a `setdefault` or
    an `update` on a nested entry changes memory and never reaches the
    file. And plain, because what comes in is a `Params` that would
    otherwise be written back into itself.
    """
    entry = _as_dict(stored)
    fitted = {
        str(board): dict(_as_dict(slots))
        for board, slots in _as_dict(entry.get("fitted")).items()
    }
    return {
        "board": str(entry.get("board", DEFAULT_BOARD)),
        "fitted": fitted,
        "recorded at": str(entry.get("recorded at", "")),
    }


def with_board(stored: object, board: str, now: str) -> dict[str, object]:
    """The record with a different board in the rack.

    The slots of the board taken out are kept: its shields are still in
    it, and putting it back should not mean recording them again.
    """
    if board_named(board) is None:
        raise ValueError(f"{board!r} is not a board: {[b.name for b in BOARDS]}")
    entry = _copy(stored)
    entry["board"] = board
    entry["recorded at"] = now
    return entry


def with_fitted(
    stored: object, board: str, slot: str, choice: str, now: str
) -> dict[str, object]:
    """The record with one slot of one board holding something else."""
    found = board_named(board)
    if found is None:
        raise ValueError(f"{board!r} is not a board: {[b.name for b in BOARDS]}")
    slots = {s.name: s for s in found.slots}
    if slot not in slots:
        raise ValueError(f"{board} has no {slot!r}: {list(slots)}")
    if slots[slot].choice(choice) is None:
        raise ValueError(
            f"{slot} cannot hold {choice!r}: {[c.name for c in slots[slot].choices]}"
        )
    entry = _copy(stored)
    fitted = entry["fitted"]
    assert isinstance(fitted, dict)
    fitted[board] = {**fitted.get(board, {}), slot: choice}
    entry["recorded at"] = now
    return entry


# --- saying it -----------------------------------------------------------


def describe(reading: Reading) -> str:
    """One line: the board, and what is in each of its slots."""
    if reading.board is None:
        return f"{reading.board_name!r} is not a board this page knows"
    if not reading.fitted:
        return reading.board.name

    voice_names = {slot.name for slot in VOICE_SLOTS}
    parts = [
        f"{name}: {held}"
        for name, held in reading.fitted.items()
        if name not in voice_names
    ]
    voices = [reading.fitted[s.name] for s in VOICE_SLOTS if s.name in reading.fitted]
    if voices and len(set(voices)) == 1:
        parts.append(f"{_VOICE_RANGE}: {voices[0]}")
    else:
        parts.extend(
            f"{s.name}: {reading.fitted[s.name]}"
            for s in VOICE_SLOTS
            if s.name in reading.fitted
        )
    return f"{reading.board.name} - " + "; ".join(parts)


def _and(names: Sequence[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def notes(reading: Reading, wired_bodies: Sequence[str]) -> dict[str, str]:
    """What follows from what is fitted, keyed by what it is about.

    Only what a document says follows. Empty when nothing needs saying,
    which is the ordinary case for the configurations the documents
    actually describe.
    """
    said: dict[str, str] = {}
    if reading.board is None:
        return said

    not_understood = []
    for slot in reading.board.slots:
        held = reading.fitted[slot.name]
        if slot.choice(held) is None:
            not_understood.append(f"{slot.name} says {held!r}")
    if not_understood:
        said["not understood"] = (
            f"{_and(not_understood)} in params.json, which is none of its "
            "choices - press what is really there"
        )

    if reading.board is SHIELDS_BACKPLANE:
        said.update(_shield_notes(reading.fitted, wired_bodies))
    elif reading.board is THOMAS_OR_TEENSY:
        said.update(_mode_notes(reading.fitted))
    return said


def _shield_notes(fitted: Mapping[str, str], wired_bodies: Sequence[str]) -> dict[str, str]:
    said = {}
    computing = fitted[COMPUTING_SLOT.name]
    analyser = fitted[ANALYSER_SLOT.name]

    if computing == EMPTY:
        said["computing"] = (
            "the computing slot is empty: nothing drives a tone, a light or a "
            "sensor, and there is no Arduino link to open"
        )
    elif computing == TEENSY_ADAPTER:
        said["computing"] = (
            "the Teensy runs firmware 5 (`shields` section 7); `drivers > "
            "arduino` and its `flash firmware` are written for the Mega's sketch"
        )

    if computing == MEGA and analyser == EMPTY:
        said["hearing"] = (
            "the Mega hears only through the analyser carrier, so with JA1 "
            "empty no body can be heard"
        )
    elif computing == TEENSY_ADAPTER and analyser == MSGEQ7_CARRIER:
        said["hearing"] = (
            "the Teensy reads the microphones directly and never the carrier, "
            "which `shields` section 10 takes out for it"
        )

    silent = [BODY_OF[s.name] for s in VOICE_SLOTS if fitted[s.name] == EMPTY]
    if silent:
        said["voices"] = (
            f"{_and(silent)} {'makes' if len(silent) == 1 else 'make'} no "
            f"sound: {'its voice slot is' if len(silent) == 1 else 'their voice slots are'} empty"
        )

    revalued = [s.name for s in VOICE_SLOTS if fitted[s.name] == REVALUED_CARD]
    if computing == MEGA and revalued:
        said["pitches"] = (
            "the Mega plays only its timers' five pitches, so the re-valued "
            f"card in {_and(revalued)} is filtering a tone it was not valued for"
        )

    if computing == MEGA:
        said.update(_wired_bodies_notes(fitted, analyser, wired_bodies))
    return said


def _wired_bodies_notes(
    fitted: Mapping[str, str], analyser: str, wired_bodies: Sequence[str]
) -> dict[str, str]:
    """`params["audio"]["wired bodies"]` against the slots.

    Two records of one fact, kept by hand in two places, so the page says
    when they disagree. It never writes either: which bodies the audio
    tests judge is a decision, and a body also needs its amplifier in,
    which nothing on this board records.
    """
    with_a_card = [
        BODY_OF[s.name]
        for s in VOICE_SLOTS
        if fitted[s.name] in (THOMAS_CARD, REVALUED_CARD)
    ]
    can_be_tested = with_a_card if analyser == MSGEQ7_CARRIER else []
    said = {}

    listed_but_not = [body for body in wired_bodies if body not in can_be_tested]
    if listed_but_not:
        if analyser != MSGEQ7_CARRIER:
            why = "the analyser slot is empty"
        elif len(listed_but_not) == 1:
            why = "its voice slot is empty"
        else:
            why = "their voice slots are empty"
        said["wired bodies"] = (
            f"`params > audio > wired bodies` lists {_and(listed_but_not)}, and "
            f"{why}: the audio tests will judge a body that cannot both sound "
            "and be heard"
        )

    not_listed = [body for body in can_be_tested if body not in wired_bodies]
    if not_listed:
        one = len(not_listed) == 1
        said["not yet wired"] = (
            f"{_and(not_listed)} {'has' if one else 'have'} a card and the "
            "analyser carrier is in, and `params > audio > wired bodies` does "
            f"not list {'it' if one else 'them'} - add "
            f"{'it' if one else 'each'} once its amplifier is in"
        )
    return said


def _mode_notes(fitted: Mapping[str, str]) -> dict[str, str]:
    said = {}
    if fitted[MODE_SHUNT.name] == TEENSY:
        if fitted[TEENSY_SOCKET.name] == EMPTY:
            said["sound"] = (
                "the shunt is on TEENSY and the socket is empty: the relays hand "
                "every body to a chain with nothing in it, so every body is silent"
            )
        else:
            said["sound"] = (
                "the Mega's tones reach nobody, so `test audio loop` and `test "
                "audio bringup` will judge silence; the Mega still drives the "
                "lights and the sensors (`thomas or teensy` section 0)"
            )
    return said
