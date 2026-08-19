"""Tests for the results browser on "test for false positives in the dark".

The test itself has always written one SVG per female next to the run's
CSV and left them there; these cover the node that puts them on the page.

This is the one place in this suite that touches a filesystem, because
what is under test is a folder scan - pytest's tmp_path, never the real
local/test results/.
"""

import pytest

from colloquy.tests.test_light_sensor_values.test_for_false_positives.results import (
    Results,
    Run,
    _inline,
)

BODIES = ("female1", "female2", "female3")
PATH = ("tests", "test for false positives in the dark", "results")

SVG = (
    '<?xml version="1.0" encoding="utf-8" standalone="no"?>\n'
    '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/x.dtd">\n'
    '<svg width="720pt" height="360pt">a picture</svg>'
)


class FakeTest:
    """What the results node asks of the test that owns it."""

    def __init__(self):
        self.owners = []
        self.plotted = []
        self.females = tuple(type("F", (), {"name": name})() for name in BODIES)

    def plot(self, file_path=None):
        self.plotted.append(file_path)


@pytest.fixture
def test_node():
    return FakeTest()


def write_run(folder, stem, bodies=BODIES):
    """One recorded run: its CSV, and a graph for each body named."""
    (folder / f"{stem}.csv").write_text("seconds, body, angle, value\n")
    for body in bodies:
        (folder / f"{body} {stem}.svg").write_text(SVG, encoding="utf-8")
    return folder / f"{stem}.csv"


# --- the folder scan -----------------------------------------------------


def test_a_recorded_run_becomes_a_child(tmp_path, test_node):
    write_run(tmp_path, "2026_08_18_14h_18min_51s")
    results = Results(owner=test_node, dir_path=tmp_path)

    children = results.snapshot_children

    assert list(children) == ["2026_08_18_14h_18min_51s"]


def test_runs_are_listed_newest_first(tmp_path, test_node):
    # The names sort as timestamps, which is the point of their shape.
    write_run(tmp_path, "2026_08_17_09h_00min_00s")
    write_run(tmp_path, "2026_08_18_14h_18min_51s")
    results = Results(owner=test_node, dir_path=tmp_path)

    assert list(results.snapshot_children) == [
        "2026_08_18_14h_18min_51s",
        "2026_08_17_09h_00min_00s",
    ]


def test_a_run_recorded_while_the_page_is_open_shows_up(tmp_path, test_node):
    write_run(tmp_path, "first")
    results = Results(owner=test_node, dir_path=tmp_path)
    assert list(results.snapshot_children) == ["first"]

    write_run(tmp_path, "second")

    assert list(results.snapshot_children) == ["second", "first"]


def test_the_same_run_keeps_its_node_across_scans(tmp_path, test_node):
    # Otherwise every request would replace the node the page is standing
    # on, and whether it is opened would be forgotten each time.
    write_run(tmp_path, "first")
    results = Results(owner=test_node, dir_path=tmp_path)

    first = results.snapshot_children["first"]
    again = results.snapshot_children["first"]

    assert first is again


def test_a_folder_that_does_not_exist_yet_is_empty(tmp_path, test_node):
    results = Results(owner=test_node, dir_path=tmp_path / "never ran")

    assert results.snapshot_children == {}


# --- what a run shows ----------------------------------------------------


def test_a_run_shows_one_graph_per_female(tmp_path, test_node):
    csv_path = write_run(tmp_path, "a run")
    run = Run(
        owner=Results(owner=test_node, dir_path=tmp_path),
        csv_path=csv_path,
        bodies=BODIES,
    )

    states = run._snapshot_if_opened(PATH)

    for body in BODIES:
        assert (
            states[body]["svg"] == '<svg width="720pt" height="360pt">a picture</svg>'
        )


def test_a_run_names_the_file_it_came_from(tmp_path, test_node):
    csv_path = write_run(tmp_path, "a run")
    run = Run(
        owner=Results(owner=test_node, dir_path=tmp_path),
        csv_path=csv_path,
        bodies=BODIES,
    )

    states = run._snapshot_if_opened(PATH)

    assert states["recorded in"]["value"] == "a run.csv"


def test_a_missing_graph_says_so_rather_than_crashing(tmp_path, test_node):
    # A run stopped early, or one whose plot never happened.
    csv_path = write_run(tmp_path, "a run", bodies=("female1",))
    run = Run(
        owner=Results(owner=test_node, dir_path=tmp_path),
        csv_path=csv_path,
        bodies=BODIES,
    )

    states = run._snapshot_if_opened(PATH)

    assert "svg" in states["female1"]
    assert states["female2"]["value"] == "no graph yet - plot again"


def test_plot_again_redraws_that_run(tmp_path, test_node):
    # Not the run that happens to have finished last - the one being
    # looked at, which is what makes an old run replottable at all.
    write_run(tmp_path, "an old run")
    results = Results(owner=test_node, dir_path=tmp_path)
    run = results.snapshot_children["an old run"]

    run.plot_again()

    assert test_node.plotted == [tmp_path / "an old run.csv"]


def test_the_xml_prologue_is_dropped_before_the_svg_goes_into_the_page(tmp_path):
    # Matplotlib writes a declaration and a DOCTYPE above the <svg>; a
    # browser parses both as bogus comments inside an HTML page.
    assert _inline(SVG).startswith("<svg")
    assert "DOCTYPE" not in _inline(SVG)


def test_something_without_a_prologue_is_left_alone():
    assert _inline("<svg/>") == "<svg/>"
