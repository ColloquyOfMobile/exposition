# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/installation_sol2/__init__.py

"""`installation PCB solution 2`: the new PCB put in, a step at a time.

A manual test in the plainest sense: the person does every step and is
the instrument for every check, and the page keeps the list, the order,
what each step must show, and what was found. Sol2 is the shields
backplane with the Teensy adapter (see `steps.py` for what that leaves
for firmware 5).

**The record is shared.** Each `done`, `not done after all` and note is
committed and pushed by the Colloquy laptop to a branch of its own, so
every checkout shows the same progress; elsewhere the page is read only.
`shared.py` says why it is a branch of its own and how it is written.

A plain `Base`, not a `BaseThread`: there is nothing to start, and a
started node under `tests` would hold off the laptop's automatic restart
for as long as it ran (`Repository.threads_in_the_way`).
"""
from colloquy.base import Base
from colloquy.markdown_document import render_markdown
from colloquy.ui import leaves

from . import progress, steps
from .shared import SharedRecord, now


def _status(entry):
    if entry.done:
        return f"done ({entry.done_at.replace('T', ' ')})"
    return "not done"


class StepNode(Base):
    """One step: what to do, whether it is done, and the note."""

    def __init__(self, owner, number, step):
        super().__init__(owner=owner)
        self._number = number
        self._step = step
        self["done"] = self.done
        self["not done after all"] = self.undo
        self["save"] = self.save

    @property
    def name(self):
        return f"{self._number:02d} {self._step.key}"

    @property
    def key(self):
        return self._step.key

    @property
    def _shared(self):
        return self.owner.shared

    def _entry(self):
        return self._shared.read().get(self.key, progress.Entry())

    def _write(self, record, summary):
        return self._shared.write(record, summary)

    def done(self, request=None):
        record = progress.mark(self._shared.read(), self.key, True, now())
        return self._write(record, f"'{self.key}' done")

    def undo(self, request=None):
        record = progress.mark(self._shared.read(), self.key, False, now())
        return self._write(record, f"'{self.key}' not done after all")

    def save(self, content):
        text = (content or "").replace("\r\n", "\n").strip()
        record = progress.annotate(self._shared.read(), self.key, text, now())
        return self._write(record, f"note on '{self.key}'")

    @property
    def snapshot_children(self):
        if not self._shared.is_writer:
            return {}
        if self._entry().done:
            return {"not done after all": self.undo}
        return {"done": self.done}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)
        entry = self._entry()
        leaf("status", _status(entry))
        leaf("phase", self._step.phase)
        states["what to do"] = leaves.html(path, "what to do", render_markdown(self._step.text))
        if self._shared.is_writer:
            states["note"] = leaves.editor(path, "note", entry.note)
        else:
            leaf("note", entry.note or "none")
        return states


class InstallationSol2(Base):
    """The guide: every step in order, and where the record stands."""

    def __init__(self, owner, shared=None):
        super().__init__(owner=owner)
        self.shared = shared if shared is not None else SharedRecord()
        self._steps = [
            StepNode(owner=self, number=number, step=step)
            for number, step in enumerate(steps.STEPS, start=1)
        ]
        for node in self._steps:
            self[node.name] = node
        self["push the record now"] = self.push_now
        self["fetch the record"] = self.fetch

    @property
    def name(self):
        return "installation PCB solution 2"

    # Its group lists which of its tests are running (`TestGroup`), and
    # asks every one. A guide never runs: there is nothing to start.
    is_started = False

    def push_now(self, request=None):
        return self.shared.push_now()

    def fetch(self, request=None):
        return self.shared.fetch()

    @property
    def snapshot_children(self):
        children = {node.name: node for node in self._steps}
        if self.shared.is_writer:
            children["push the record now"] = self.push_now
        else:
            children["fetch the record"] = self.fetch
        return children

    def _table(self, record, next_key):
        rows = []
        phase = None
        for node in self._steps:
            if node._step.phase != phase:
                phase = node._step.phase
                rows.append(f"<tr><th colspan='3'>{phase}</th></tr>")
            entry = record.get(node.key, progress.Entry())
            mark = "&#10003;" if entry.done else ("&#8594;" if node.key == next_key else "")
            note = "&#9998;" if entry.note else ""
            rows.append(
                f"<tr><td>{mark}</td><td>{node.name}</td><td>{note}</td></tr>"
            )
        return "<table>" + "".join(rows) + "</table>"

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)
        record = self.shared.read()
        next_key = progress.next_step(record, steps.KEYS)
        done = sum(1 for key in steps.KEYS if record.get(key, progress.Entry()).done)
        leaf("progress", f"{done} of {len(steps.KEYS)} steps done")
        if next_key is None:
            leaf("next step", "none - every step is done")
        else:
            number = steps.KEYS.index(next_key) + 1
            leaf("next step", f"{number:02d} {next_key}")
        leaf("record", self.shared.where())
        if self.shared.report:
            leaf("last write", self.shared.report)
        states["steps"] = leaves.html(path, "steps", self._table(record, next_key))
        return states
