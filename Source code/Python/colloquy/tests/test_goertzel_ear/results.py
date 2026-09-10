# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_goertzel_ear/results.py

"""Every run this test has recorded, newest first.

The run that has just finished is already on the test's own page as
`recording` - it is the one you want without going to look for it. This
is the other want, and it is the one that made a file worth writing:
comparing runs. Is the 6250 Hz bin always the weak one, did moving the
microphone help, is it worse than it was last week. In memory the answer
was always "there is only this run", because `setup()` clears the
recording and a restart takes it anyway.

Same shape as `test_light_sensor_values/results.py`, and for the same
reason: a folder of CSVs nothing in the tree points at is a folder nobody
opens. Rescanned on every request, so a run that finishes while the page
is open turns up without a restart - and so does one copied over from the
other computer.

**A run's graph is built from its file, and only when it is opened.** The
parse is a few hundred rows and the listing may be long, so paying for
every run's arithmetic to draw a list of names would be the cost the
paging in `graph_view.py` exists to avoid. Kept once built, because a
`GraphView` holds which page the reader is on.
"""
from colloquy.base import Base
from colloquy.ui import leaves
from colloquy.ui.graph_view import GraphView

from . import recording


class Run(Base):
    """One recorded run: the levels, the presses, and the graph of both."""

    def __init__(self, owner, csv_path):
        super().__init__(owner=owner)
        self._csv_path = csv_path
        self._graph = None

    @property
    def name(self):
        return self._csv_path.stem

    @property
    def csv_path(self):
        return self._csv_path

    @property
    def graph(self):
        """This run drawn, read off the disk on first ask.

        None when the file holds no readable block - a truncated write, or
        a file emptied by hand. An absent node says that better than a
        picture with nothing in it.
        """
        if self._graph is None:
            series, marks = recording.read(self._csv_path)
            if not any(len(points) for _label, points in series):
                return None
            self._graph = GraphView(
                owner=self, series=series, marks=marks, name="recording"
            )
        return self._graph

    @property
    def snapshot_children(self):
        graph = self.graph
        return {} if graph is None else {graph.name: graph}

    def _snapshot_if_opened(self, path):
        # From Base's, so the graph is listed as a child. A dict of its
        # own here would mean this node could never have one.
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        leaf("recorded in", self._csv_path.name)

        graph = self.graph
        if graph is None:
            leaf("read", "nothing readable in this file")
            return states

        marks = graph.marks
        leaf("blocks", graph.length)
        leaf(
            "presses",
            ", ".join(f"{label} at {moment:.1f}s" for moment, label in marks)
            if marks
            else "none - nothing was played during this run",
        )
        # Said on every run rather than only in the docstring, because a
        # file is exactly the thing that outlives the person who knows it.
        leaf(
            "not in this file",
            "whether anybody heard the tone come out of the speakers",
        )
        return states


class Results(Base):
    """The recorded runs, newest first."""

    def __init__(self, owner, dir_path):
        super().__init__(owner=owner)
        self._dir_path = dir_path
        self._children = {}

    @property
    def name(self):
        return "results"

    @property
    def snapshot_children(self):
        if not self._dir_path.exists():
            return {}

        found = {}
        for csv_path in sorted(self._dir_path.glob("*.csv"), reverse=True):
            key = csv_path.stem
            # Kept across requests where it already exists, so opening a
            # run and paging into it survives the next click.
            found[key] = self._children.get(key) or Run(
                owner=self, csv_path=csv_path
            )

        self._children = found
        return dict(self._children)
