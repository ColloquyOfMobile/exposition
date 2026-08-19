# -*- coding: utf-8 -*-
# colloquy/tests/test_light_sensor_values/test_for_false_positives/results.py

"""The graphs this test draws, reachable from the page.

`plot()` has always written one SVG per female next to the run's CSV, in
local/test results/..., and nothing in the tree ever pointed at them - so
the answer to the question the test asks ("does a female read light in
the dark?") could only be had by opening the folder by hand.

One node per run, newest first, each showing its three graphs. The files
are read as they were written rather than redrawn, so what the page shows
is the run's own record; `plot again` redraws them from the CSV, which is
what a run wants after the threshold in params has moved, or if its plot
never happened.
"""

from colloquy.base import Base
from colloquy.ui import leaves


def _inline(svg_text):
    """Matplotlib writes an XML declaration and a DOCTYPE above the <svg>.

    Both are meaningless inside an HTML page - a browser parses them as
    bogus comments - so drop everything before the opening tag.
    """
    start = svg_text.find("<svg")
    return svg_text if start == -1 else svg_text[start:]


class Run(Base):
    """One run: its CSV, and the graph each female got out of it."""

    def __init__(self, owner, csv_path, bodies):
        super().__init__(owner=owner)
        self._csv_path = csv_path
        self._bodies = tuple(bodies)
        self["plot again"] = self.plot_again

    @property
    def name(self):
        return self._csv_path.stem

    @property
    def snapshot_children(self):
        return {}

    def graph_path(self, body):
        return self._csv_path.with_name(f"{body} {self._csv_path.stem}.svg")

    def plot_again(self, request=None):
        """Redraw all three graphs from this run's CSV."""
        self.owner.test.plot(file_path=self._csv_path)

    def _snapshot_if_opened(self, path):
        states = {"plot again": self.plot_again}
        leaf = leaves.into(states, path)
        leaf("recorded in", self._csv_path.name)

        for body in self._bodies:
            graph = self.graph_path(body)
            if not graph.is_file():
                leaf(body, "no graph yet - plot again")
                continue
            states[body] = leaves.svg(
                path, body, _inline(graph.read_text(encoding="utf-8"))
            )
        return states


class Results(Base):
    """Every run this test has recorded, newest first.

    Rescanned on every request, like the timeline browser: a run that
    finishes while the page is open shows up without a restart, and so
    does one copied in from the installation's machine.
    """

    def __init__(self, owner, dir_path):
        super().__init__(owner=owner)
        self._dir_path = dir_path
        self._children = {}

    @property
    def name(self):
        return "results"

    @property
    def test(self):
        return self.owner

    @property
    def bodies(self):
        # Asked for when a run is built rather than when this node is,
        # which is before the hardware is reachable from here.
        return tuple(female.name for female in self.test.females)

    @property
    def snapshot_children(self):
        if not self._dir_path.exists():
            return {}

        found = {}
        for csv_path in sorted(self._dir_path.glob("*.csv"), reverse=True):
            key = csv_path.stem
            found[key] = self._children.get(key) or Run(
                owner=self, csv_path=csv_path, bodies=self.bodies
            )

        self._children = found
        return dict(self._children)
