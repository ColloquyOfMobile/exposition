# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/scope/results.py

"""Every run the scope has recorded, newest first.

The run that has just finished is already on the scope's own page as
`trace` - it is the one you want without going to look for it. This is
the other want, and it is the one that made a file worth writing at all:
comparing runs. Is A1 still quiet after reseating it, was it this bad
before the lead was moved, did the difference follow the lead when the two
were swapped. In memory the answer was always "there is only this run".

Same shape as `test_goertzel_ear/results.py` and
`test_light_sensor_values/results.py`, for the same reason: a folder of
CSVs nothing in the tree points at is a folder nobody opens. Rescanned on
every request, so a run that finishes while the page is open turns up
without a restart - and so does one copied over from the other computer.

**A run's graph is built from its file, and only when it is opened.** A
scope run is a hundred thousand rows; parsing every one of them to draw a
*list of names* would be exactly the cost the paging in `graph_view.py`
exists to avoid. Kept once built, because a `GraphView` holds which page
the reader is on.
"""
from colloquy.base import Base
from colloquy.ui import leaves
from colloquy.ui.graph_view import GraphView

from . import recording, trace
from .trace import describe_coupling


class Run(Base):
    """One recorded run: both channels, and the graph of them."""

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

        None when the file holds no readable row - a truncated write, or a
        file emptied by hand. An absent node says that better than a
        picture with nothing in it.
        """
        if self._graph is None:
            series = recording.read(self._csv_path)
            if not any(len(points) for points in series.values()):
                return None
            self._graph = GraphView(owner=self, series=series, name="trace")
        return self._graph

    @property
    def snapshot_children(self):
        graph = self.graph
        return {} if graph is None else {graph.name: graph}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)
        leaf("file", str(self._csv_path))
        leaf("size", recording.describe(self._csv_path))

        graph = self.graph
        if graph is None:
            leaf("rows", "none that could be read - the file is empty or cut")
            return states

        lines = graph.series
        leaf("rows", f"{max(len(points) for _label, points in lines):,} a channel")
        for label, points in lines:
            values = [value for _x, value in points]
            leaf(
                str(label),
                f"{min(values)} to {max(values)} of 1023, "
                f"swing {max(values) - min(values)}",
            )
        leaf("independent", self._coupling(lines))
        return states

    @staticmethod
    def _coupling(lines):
        """The same check the live page makes, on a run read off the disk.

        Computed from the rows rather than stored in the file: it is
        arithmetic over the samples, and a number written into a CSV is a
        number that can later disagree with the rows beneath it.
        """
        if len(lines) < 2:
            return "only one channel in this file"
        columns = [[value for _x, value in points] for _label, points in lines]
        seconds = [x for x, _value in lines[0][1]]
        names = tuple(str(label) for label, _points in lines)
        return describe_coupling(
            trace.coupling_of(columns[0], columns[1], seconds), names
        )


class Results(Base):
    """The folder, as a list of runs."""

    def __init__(self, owner, dir_path):
        super().__init__(owner=owner)
        self._dir_path = dir_path
        self._children = {}

    @property
    def name(self):
        return "results"

    @property
    def runs(self):
        """Newest first, and **the same objects as last request**.

        Rescanned every time, so a run that finished while the page was
        open is simply there - but a run already listed keeps the node it
        had. That is not an optimisation. A `GraphView` holds which page
        and which zoom the reader is on, so a node rebuilt on every
        request means every press of `next page` mutates a graph that is
        then thrown away and redrawn at page one: the links answer, the
        readings change for one render, and the picture never moves.
        Building fresh is the obvious way to write this and it is silently
        wrong, which is why the same line is in
        `test_goertzel_ear/results.py`.
        """
        if not self._dir_path.exists():
            self._children = {}
            return []

        found = {}
        for csv_path in sorted(self._dir_path.glob("*.csv"), reverse=True):
            key = csv_path.stem
            found[key] = self._children.get(key) or Run(
                owner=self, csv_path=csv_path
            )
        self._children = found
        return list(found.values())

    @property
    def snapshot_children(self):
        return {run.name: run for run in self.runs}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)
        runs = self.runs
        leaf("folder", str(self._dir_path))
        leaf(
            "runs",
            f"{len(runs)}" if runs else "none yet - a run is written when you "
            "press stop",
        )
        return states
