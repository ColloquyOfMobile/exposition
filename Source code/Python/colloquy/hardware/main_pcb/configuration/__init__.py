# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/main_pcb/configuration/__init__.py

"""Which board is in the rack, and what is plugged into it.

The same kind of fact as `main pcb`'s mounted flag, and kept the same
way: a note in params.json, written by a press, cleared by nothing but
another press. **Nothing in the hardware can answer it** - `shields`
says outright that the silkscreen is the only identification a shield
has - so the page holds the record the silkscreen box holds at the rack,
and somebody who has just changed a shield writes it in both.

**The rack is a slot too.** It takes a board (`board`), and a board may
have slots of its own: the shields backplane takes a computing shield,
the analyser carrier and five voice cards; the thomas-or-teensy board
has its mode shunt and its Teensy socket. Each is one node with a press
for everything it could hold *instead*, so the page offers only the
presses that change something - `main pcb`'s rule. A board's own slots
appear only while it is the board in the rack.

**It is a record and drives nothing.** Recording a Teensy does not stop
`main.py` reaching for a Mega, and recording an empty voice slot does
not take that body out of `audio > wired bodies`. What follows from a
configuration is *said* - one reading per consequence, each taken from
the board's own document - and acting on it stays a decision for whoever
is standing there. The one place two hand-kept records describe the
same fact (a body's voice card against the wired-bodies list) is
compared rather than reconciled, for the same reason.

Not gated by `is_simulated`, for `hardware`'s reason: the machine with
the board in it is where none of this is hypothetical.
"""
import html
from datetime import datetime
from functools import partial

from colloquy.base import Base
from colloquy.ui import leaves

from . import table

# Where the board documents hang, for the links to them.
_ELECTRONICS_PATH = "/app/hardware/electronics"


class SlotNode(Base):
    """One slot, what it holds, and a press for each thing it could hold
    instead."""

    def __init__(self, owner, slot, board=None):
        super().__init__(owner=owner)
        self._slot = slot
        # None for the rack itself, whose slot takes a board.
        self._board = board

    @property
    def name(self):
        return self._slot.name

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def held(self):
        return self.owner.held_in(self._board, self._slot)

    def choose(self, choice, request=None):
        return self.owner.record(self._board, self._slot, choice)

    @property
    def snapshot_children(self):
        held = self.held
        return {
            choice.name: partial(self.choose, choice.name)
            for choice in self._slot.choices
            if choice.name != held
        }

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        held = self.held
        choice = self._slot.choice(held)
        if choice is None:
            leaf(
                "fitted",
                f"{held!r}, which is none of the choices - press what is really there",
            )
        else:
            leaf("fitted", f"{choice.name} - {choice.says}")

        others = [c for c in self._slot.choices if c.name != held]
        states["instead"] = leaves.html(
            path,
            "instead",
            "".join(
                f"<p><strong>{html.escape(c.name)}</strong>: {html.escape(c.says)}</p>"
                for c in others
            ),
        )
        return states


class Configuration(Base):
    """The record of what is in the rack, and what follows from it."""

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._board_node = SlotNode(owner=self, slot=table.RACK)
        # One node per slot of every board, built once. Only the board in
        # the rack has its own drawn, but the others keep what was last
        # recorded for them: a board taken out still has its shields in.
        self._slot_nodes = {
            board.name: [SlotNode(owner=self, slot=slot, board=board.name) for slot in board.slots]
            for board in table.BOARDS
        }
        self[self._board_node.name] = self._board_node

    @property
    def name(self):
        return "configuration"

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def _pcb_params(self):
        return self.owner.params

    @property
    def reading(self):
        return table.read(self._pcb_params.get("configuration"))

    def held_in(self, board, slot):
        """What a slot holds: the board in the rack when `board` is None."""
        stored = self._pcb_params.get("configuration")
        if board is None:
            return table.read(stored).board_name
        return table.fitted_on(stored, board)[slot.name]

    def record(self, board, slot, choice):
        """Write one press down. Returns a sentence the tree throws away;
        the re-rendered node, reading `fitted`, is what the reader sees."""
        now = datetime.now().isoformat(timespec="seconds")
        stored = self._pcb_params.get("configuration")
        if board is None:
            entry = table.with_board(stored, choice, now)
            said = f"The rack is noted as holding: {choice}."
        else:
            entry = table.with_fitted(stored, board, slot.name, choice, now)
            said = f"The {board}'s {slot.name} is noted as holding: {choice}."
        # Whole, in one assignment: only assignment saves params.json.
        self._pcb_params["configuration"] = entry
        self.log(said)
        return said

    @property
    def wired_bodies(self):
        try:
            listed = self.colloquy.params["audio"]["wired bodies"]
        except (KeyError, TypeError):
            return []
        return [str(body) for body in listed] if isinstance(listed, list) else []

    @property
    def summary(self):
        return table.describe(self.reading)

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        children = {self._board_node.name: self._board_node}
        for node in self._slot_nodes.get(self.reading.board_name, []):
            children[node.name] = node
        return children

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)
        reading = self.reading

        leaf("in the rack", table.describe(reading))
        leaf(
            "recorded",
            reading.recorded_at
            or "never - this is the default, not something anybody has said",
        )
        if reading.board is None:
            return states

        if reading.board.documents:
            states["described in"] = leaves.html(
                path,
                "described in",
                "<p>"
                + ", ".join(
                    f'<a href="{_ELECTRONICS_PATH}/{name}">{html.escape(name)}</a>'
                    for name in reading.board.documents
                )
                + "</p>",
            )
        if reading.board.changing:
            leaf("changing what is fitted", reading.board.changing)
        for topic, sentence in table.notes(reading, self.wired_bodies).items():
            leaf(topic, sentence)
        return states
