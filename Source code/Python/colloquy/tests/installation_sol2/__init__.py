# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/installation_sol2/__init__.py

"""`installation PCB solution 2`: the new PCB put in, a step at a time.

A manual test in the plainest sense: the person does every step and is
the instrument for every check, and the page keeps the list, the order,
what each step must show, and what was found. Sol2 is the shields
backplane with the Teensy adapter (see `steps.py` for what that leaves
for firmware 5).

**The guide's own page is "resume where you left off".** It shows the
first step not done - its picture, what to do, its note - with `done:
next step` beside it. A tree command re-renders the node it was pressed
on (`ui/tree.update`), and that is exactly what makes `done` go on: the
guide re-drawn after the press shows the step after. Below it, the whole
list, ticked. Every step also has a page of its own under `all steps`,
for going back to one; once done, it links on to the step after.

**The record is shared.** Each `done`, `not done after all` and note is
committed and pushed by the Colloquy laptop to a branch of its own, so
every checkout shows the same progress; elsewhere the page is read only.
`shared.py` says why it is a branch of its own and how it is written.

A plain `Base`, not a `BaseThread`: there is nothing to start, and a
started node under `tests` would hold off the laptop's automatic restart
for as long as it ran (`Repository.threads_in_the_way`).
"""
from html import escape
from urllib.parse import quote

from colloquy.base import Base
from colloquy.markdown_document import render_markdown
from colloquy.ui import leaves

from . import pictures, progress, steps
from .shared import SharedRecord, now


def _when(at):
    return at.replace("T", " ")


def _status(entry):
    return f"done ({_when(entry.done_at)})" if entry.done else "not done"


def _href(node):
    """The page of a node, as the console addresses it."""
    try:
        return "/app/" + quote(node.path.as_posix())
    except Exception:  # noqa: BLE001 - a link must not stop a render
        return "#"


def _step_html(number, step, entry):
    """Title, picture and instructions of one step, as one block."""
    title = f"{number:02d} {escape(step.key)}"
    status = "&#10003; " + escape(_status(entry)) if entry.done else escape(step.phase)
    return (
        f"<h3>{title}</h3><p><em>{status}</em></p>"
        f"{pictures.picture(step.key)}"
        f"{render_markdown(step.text)}"
    )


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
    def number(self):
        return self._number

    @property
    def step(self):
        return self._step

    @property
    def _guide(self):
        return self.owner.owner

    @property
    def _shared(self):
        return self._guide.shared

    def _entry(self):
        return self._shared.read().get(self.key, progress.Entry())

    def done(self, request=None):
        return self._guide.mark(self.key, True)

    def undo(self, request=None):
        return self._guide.mark(self.key, False)

    def save(self, content):
        return self._guide.annotate(self.key, content)

    @property
    def snapshot_children(self):
        if not self._shared.is_writer:
            return {}
        if self._entry().done:
            return {"not done after all": self.undo}
        return {"done": self.done}

    def _snapshot_if_opened(self, path):
        # Read first, buttons after: the children (`done`) are drawn in
        # the order they are put in.
        children = super()._snapshot_if_opened(path)
        states = {}
        entry = self._entry()
        states["what to do"] = leaves.html(
            path, "what to do", _step_html(self._number, self._step, entry)
        )
        if self._shared.is_writer:
            states["note"] = leaves.editor(path, "note", entry.note)
        else:
            leaves.into(states, path)("note", entry.note or "none")
        states.update(children)
        if entry.done:
            states["go on"] = leaves.html(path, "go on", self._guide.go_on_html())
        return states


class AllSteps(Base):
    """Every step's own page, in order. Here so the guide's page can draw
    the list once, ticked, instead of a second time as bare links."""

    def __init__(self, owner, nodes):
        super().__init__(owner=owner)
        self._nodes = nodes
        for node in nodes:
            self[node.name] = node

    @property
    def name(self):
        return "all steps"

    @property
    def snapshot_children(self):
        return {node.name: node for node in self._nodes}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        states["steps"] = leaves.html(path, "steps", self.owner.table_html())
        return states


class InstallationSol2(Base):
    """The guide: where you left off, then every step, ticked."""

    def __init__(self, owner, shared=None):
        super().__init__(owner=owner)
        self.shared = shared if shared is not None else SharedRecord()
        self._nodes = []
        self._all = AllSteps(owner=self, nodes=self._nodes)
        for number, step in enumerate(steps.STEPS, start=1):
            node = StepNode(owner=self._all, number=number, step=step)
            self._nodes.append(node)
            self._all[node.name] = node
        self[self._all.name] = self._all
        self["done: next step"] = self.done_current
        self["back one step"] = self.back_one
        self["save"] = self.save
        self["push the record now"] = self.push_now
        self["fetch the record"] = self.fetch

    @property
    def name(self):
        return "installation PCB solution 2"

    # Its group lists which of its tests are running (`TestGroup`), and
    # asks every one. A guide never runs: there is nothing to start.
    is_started = False

    # --- the record ----------------------------------------------------

    def _current(self, record=None):
        """The node of the first step not done, or None when all are."""
        record = self.shared.read() if record is None else record
        key = progress.next_step(record, steps.KEYS)
        return None if key is None else self._nodes[steps.KEYS.index(key)]

    def mark(self, key, done):
        record = progress.mark(self.shared.read(), key, done, now())
        what = "done" if done else "not done after all"
        return self.shared.write(record, f"'{key}' {what}")

    def annotate(self, key, content):
        text = (content or "").replace("\r\n", "\n").strip()
        record = progress.annotate(self.shared.read(), key, text, now())
        return self.shared.write(record, f"note on '{key}'")

    # --- presses -------------------------------------------------------

    def done_current(self, request=None):
        current = self._current()
        if current is None:
            return "every step is done"
        return self.mark(current.key, True)

    def back_one(self, request=None):
        """Untick the step before the current one, which brings it back as
        the current step: for a `done` pressed too soon."""
        record = self.shared.read()
        current = self._current(record)
        index = len(self._nodes) if current is None else current.number - 1
        for node in reversed(self._nodes[:index]):
            if record.get(node.key, progress.Entry()).done:
                return self.mark(node.key, False)
        return "nothing before this step is done"

    def save(self, content):
        current = self._current()
        if current is None:
            return "every step is done - open the step under 'all steps' to change its note"
        return self.annotate(current.key, content)

    def push_now(self, request=None):
        return self.shared.push_now()

    def fetch(self, request=None):
        return self.shared.fetch()

    # --- drawing -------------------------------------------------------

    def table_html(self):
        record = self.shared.read()
        current = self._current(record)
        rows = []
        phase = None
        for node in self._nodes:
            if node.step.phase != phase:
                phase = node.step.phase
                rows.append(f"<tr><th colspan='3'>{escape(phase)}</th></tr>")
            entry = record.get(node.key, progress.Entry())
            if entry.done:
                mark = "&#10003;"
            elif node is current:
                mark = "&#8594;"
            else:
                mark = ""
            name = escape(node.name)
            if node is current:
                name = f"<strong>{name}</strong>"
            note = f"<span title='{escape(entry.note)}'>&#9998;</span>" if entry.note else ""
            rows.append(
                f"<tr><td>{mark}</td><td><a href='{_href(node)}'>{name}</a></td>"
                f"<td>{note}</td></tr>"
            )
        return "<table>" + "".join(rows) + "</table>"

    def go_on_html(self):
        current = self._current()
        guide = f"<a href='{_href(self)}'>resume where you left off</a>"
        if current is None:
            return f"<p>Every step is done. {guide}.</p>"
        return (
            f"<p>Next: <a href='{_href(current)}'>{escape(current.name)}</a> "
            f"&#183; {guide}</p>"
        )

    @property
    def snapshot_children(self):
        children = {}
        if self.shared.is_writer:
            current = self._current()
            if current is not None:
                children["done: next step"] = self.done_current
            children["back one step"] = self.back_one
        children[self._all.name] = self._all
        if self.shared.is_writer:
            children["push the record now"] = self.push_now
        else:
            children["fetch the record"] = self.fetch
        return children

    def _snapshot_if_opened(self, path):
        children = super()._snapshot_if_opened(path)
        states = {}
        leaf = leaves.into(states, path)
        record = self.shared.read()
        current = self._current(record)
        done = sum(1 for key in steps.KEYS if record.get(key, progress.Entry()).done)
        leaf("progress", f"{done} of {len(steps.KEYS)} steps done")
        leaf("record", self.shared.where())
        if self.shared.report:
            leaf("last write", self.shared.report)

        if current is None:
            states["where you left off"] = leaves.html(
                path, "where you left off", "<p>&#10003; Every step is done.</p>"
            )
        else:
            entry = record.get(current.key, progress.Entry())
            states["where you left off"] = leaves.html(
                path, "where you left off", _step_html(current.number, current.step, entry)
            )
            if self.shared.is_writer:
                states["note"] = leaves.editor(path, "note", entry.note)
            elif entry.note:
                leaf("note", entry.note)
        states.update(children)
        states["steps"] = leaves.html(path, "steps", self.table_html())
        return states
