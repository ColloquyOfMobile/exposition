# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware_tests/test_light_sensor_results_graph.py

"""The run's raw reading is drawn by the server, not by the browser.

`test_with_everything_moving` records three females' light sensors for
several minutes and then offers the whole thing to look at. That picture
used to be a uPlot `chart` leaf - every sample serialised into the page
so the browser could decide what to draw - and it is now a `GraphView`,
which keeps the data here and sends only the window asked for.

What is worth pinning is what changed: that it is a *node* (it has
controls, so it cannot be a leaf), that all three females are on it, and
that nothing about the run's numbers was lost on the way.
"""
import math

from types import SimpleNamespace

import pytest

from colloquy.tests.test_light_sensor_values.utils import FEMALE_COLUMNS
# Aliased: pytest tries to collect anything named Test* it finds in a
# test module, and this one has an __init__.
from colloquy.tests.test_light_sensor_values.test_with_everything_moving.test_results import (
    TestResults as LightSensorResults,
)
from colloquy.ui.graph_view import Columns, GraphView


ROWS = [
    (
        i * 0.05,
        300 + 40 * math.sin(i / 40),
        300 + 40 * math.sin(i / 30),
        300 + 40 * math.sin(i / 20),
    )
    for i in range(2000)
]


@pytest.fixture
def results():
    return LightSensorResults(owner=SimpleNamespace(owner=None, owners=[]), result_rows=ROWS)


def test_the_full_measurement_is_a_graph_node(results):
    """A node rather than a leaf, because it has commands on it - the
    density, the zoom and the scroll - and the tree draws a thing you can
    act on as something you open."""
    children = results.snapshot_children

    assert list(children) == ["full measurement"]
    assert isinstance(children["full measurement"], GraphView)


def test_every_female_is_on_it_under_her_own_name(results):
    graph = results.snapshot_children["full measurement"]

    assert [label for label, _ in graph.series] == list(FEMALE_COLUMNS)


def test_it_looks_at_the_dataframe_rather_than_copying_it(results):
    """A forty-minute run is a hundred thousand rows and the graph draws
    four hundred of them; holding the log twice to do that is the thing
    `Columns` exists to avoid."""
    graph = results.snapshot_children["full measurement"]

    assert all(isinstance(points, Columns) for _label, points in graph.series)


def test_it_pages_through_the_run(results):
    graph = results.snapshot_children["full measurement"]
    assert graph.page_count == 1              # opens on the whole of it

    graph.smaller_page()
    assert graph.page_count > 1
    first = graph.x_window

    graph.next_page()
    assert graph.x_window[0] > first[0]


def test_it_holds_every_sample_the_run_recorded(results):
    """The point of drawing it here: nothing is thinned until a page asks
    for it, and the whole log stays on this side of the wire."""
    graph = results.snapshot_children["full measurement"]

    assert graph.held == len(ROWS) * len(FEMALE_COLUMNS)
    assert len(graph.drawn()) < graph.held


def test_the_readings_survived_the_dataframe(results):
    graph = results.snapshot_children["full measurement"]
    _label, points = graph.series[0]

    assert points[0] == (ROWS[0][0], ROWS[0][1])
    assert points[-1] == (ROWS[-1][0], ROWS[-1][1])


def test_no_chart_data_is_serialised_into_the_page(results):
    """What it stopped doing. A `chart` leaf ships every point as JSON;
    this one ships a picture of the window."""
    states = results._snapshot_if_opened(("tests", "test results"))

    assert not any("chart" in leaf for leaf in states.values())
