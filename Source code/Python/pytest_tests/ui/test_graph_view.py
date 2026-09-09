# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/ui/test_graph_view.py

"""A chart that needs no script, and keeps the data on the server.

This is now the whole of the page's charting - uPlot was retired on
2026-09-09 - so what is worth pinning is what it does that a client-side
chart cannot: the window is chosen *here*, before anything is rendered,
and only the window is ever built. Two numbers do that, and they are
different questions:

- the **page size**, in samples, which is the x axis;
- the **points**, which is how many of that page get drawn.

Set the page at or below the points and nothing is thinned - full
density, a few hundred points on the wire. That combination is the whole
reason the page size is a control, and most of what is checked below.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

from colloquy.server2.wsgi2 import WSGI2
from colloquy.ui.wsgi import MockWSGI
from colloquy.ui.graph_view import (
    DEFAULT_POINTS,
    PAGE_CHOICES,
    POINT_CHOICES,
    Columns,
    GraphView,
    dummy_marks,
    dummy_series,
)

PATH = ("tests", "test graph")


def graph(**kwargs):
    return GraphView(owner=SimpleNamespace(owner=None, owners=[]), **kwargs)


@pytest.fixture(params=(WSGI2, MockWSGI), ids=("installation", "mock"))
def renderer(request):
    """The markup one of the two pages draws for this node, built the way
    pytest_tests/ui/test_leaves.py builds it - through __new__, since the
    renderer only ever reads dicts and none of a request is wanted."""
    renderer_class = request.param

    def render(states):
        page = renderer_class.__new__(renderer_class)
        page._base_path = Path("tests")
        page._root = Path("app")
        return page._html_recursion(
            {"path": PATH, "name": "graph", "opened": True, **states}
        )

    return render


# --- the data ------------------------------------------------------------


def test_the_dummy_data_is_the_same_every_time():
    """Paging around it has to be paging around one dataset, and the two
    computers have to see the same picture."""
    assert dummy_series(samples=50) == dummy_series(samples=50)


def test_it_has_something_to_find_at_more_than_one_scale():
    """Paging in is only worth having if there is structure under it: a
    slow sweep to see on one page, pulses a few pages in, noise at the
    bottom."""
    values = [value for _, value in dummy_series()]

    assert max(values) - min(values) > 400        # the sweep
    steps = [abs(b - a) for a, b in zip(values, values[1:])]
    assert max(steps) > 100                       # a pulse edge
    assert min(steps) < 5                         # and fine detail


# --- what the server decides ---------------------------------------------


def test_it_opens_on_the_whole_run_at_a_readable_density():
    """The first thing anybody wants is the shape of the lot; looking
    closely is what the page size is for."""
    view = graph()

    assert view.page_size is None
    assert view.page_count == 1
    assert view.in_window == view.held > DEFAULT_POINTS
    assert len(view.drawn()) == DEFAULT_POINTS


def test_a_smaller_page_narrows_the_window_and_the_work():
    view = graph()
    view.smaller_page()

    # The largest size that actually splits this much data - a page as
    # big as the run is the view it already had.
    assert view.page_size == max(n for n in PAGE_CHOICES if n and n < view.held)
    assert view.in_window < view.held
    # Still the same number drawn - the reader asked for that many, and
    # the page got denser rather than the picture sparser.
    assert len(view.drawn()) == DEFAULT_POINTS


def test_the_density_is_the_readers_to_change():
    view = graph()

    view.fewer_points()
    assert len(view.drawn()) < DEFAULT_POINTS

    view.more_points()
    view.more_points()
    assert len(view.drawn()) > DEFAULT_POINTS


def test_the_density_stops_at_the_ends_rather_than_running_away():
    view = graph()
    for _ in range(20):
        view.fewer_points()
    assert len(view.drawn()) == POINT_CHOICES[0]

    for _ in range(20):
        view.more_points()
    assert view._wanted == POINT_CHOICES[-1]


# --- the point of the page size ------------------------------------------


def test_a_page_no_bigger_than_the_points_draws_every_sample():
    """The state the whole control exists for: full density, nothing
    thinned, and still only a few hundred points in the picture."""
    view = graph()
    while view.page_size is None or view.page_size > DEFAULT_POINTS:
        view.smaller_page()

    assert view.in_window <= DEFAULT_POINTS
    assert len(view.drawn()) == view.in_window


def test_and_it_says_so_rather_than_leaving_two_numbers_to_be_compared():
    view = graph()
    while view.page_size is None or view.page_size > DEFAULT_POINTS:
        view.smaller_page()

    states = view._snapshot_if_opened(PATH)
    assert states["density"]["value"] == "every sample on this page is drawn"


def test_a_big_page_has_no_such_claim_on_it():
    states = graph()._snapshot_if_opened(PATH)

    assert "density" not in states


def test_only_the_page_is_ever_built():
    """The reason a forty-minute run costs the same to draw as a ten
    second one: nothing reads a row it is not going to put on screen."""
    counted = Counting(dummy_series(samples=2000))
    view = graph(series=[("counted", counted)])
    while view.page_size is None or view.page_size > 500:
        view.smaller_page()

    # The value axis is the one thing that does need every row, so that
    # it means the same from page to page. It is scanned once and kept.
    view.svg()
    first_render = counted.reads
    assert first_render > len(counted)

    counted.reads = 0
    view.svg()
    view.next_page()
    view.svg()

    # Two pictures and a page turn, for a few hundred rows each and two
    # for each window's edges - nowhere near the two thousand held, and
    # no second scan.
    assert counted.reads < 2 * DEFAULT_POINTS + 20


class Counting:
    """A series that says how often it was asked for a row."""

    def __init__(self, points):
        self._points = points
        self.reads = 0

    def __len__(self):
        return len(self._points)

    def __getitem__(self, index):
        self.reads += 1
        return self._points[index]


# --- moving along --------------------------------------------------------


def test_paging_walks_along_x_without_leaving_the_data():
    view = graph()
    view.smaller_page()
    view.smaller_page()
    start, _end = view.x_window

    view.next_page()
    moved, _end = view.x_window
    assert moved > start

    for _ in range(200):
        view.next_page()
    assert view.page == view.page_count - 1
    assert view.x_window[1] <= view.full_x[1] + 1e-9


def test_the_ends_are_one_press_away():
    view = graph()
    view.smaller_page()
    view.smaller_page()

    view.last_page()
    assert view.page == view.page_count - 1

    view.first_page()
    assert view.page == 0
    assert view.page_range()[0] == 0


def test_previous_page_stops_at_the_first_rather_than_going_negative():
    view = graph()
    view.smaller_page()

    view.previous_page()

    assert view.page == 0


def test_resizing_the_page_keeps_the_reader_where_they_were_looking():
    """The first row on screen is the anchor, not the page number: on a
    smaller page, "page 3" is somewhere else entirely."""
    view = graph()
    view.smaller_page()
    view.next_page()
    view.next_page()
    first_row, _stop = view.page_range()

    view.smaller_page()

    assert view.page_range()[0] == first_row


def test_the_last_page_survives_a_bigger_page():
    """The count shrinks when the size grows, and a reader at the end
    should land on the new end rather than off it."""
    view = graph()
    view.smaller_page()
    view.smaller_page()
    view.last_page()

    view.bigger_page()

    assert 0 <= view.page < view.page_count


def test_a_page_as_big_as_the_run_is_not_offered_as_a_size():
    """It is the view `None` already is, so a press that landed on one
    would look like nothing happening."""
    view = graph(points=dummy_series(samples=300))

    assert view.page_choices() == (100, 250, None)


def test_a_run_too_short_to_page_says_so_by_offering_nothing_else():
    view = graph(points=dummy_series(samples=50))

    assert view.page_choices() == (None,)
    view.smaller_page()
    assert view.page_size is None


def test_the_page_size_stops_at_both_ends():
    view = graph()
    for _ in range(20):
        view.smaller_page()
    assert view.page_size == PAGE_CHOICES[0]

    for _ in range(20):
        view.bigger_page()
    assert view.page_size is None


def test_reset_puts_the_whole_run_back_on_one_page():
    view = graph()
    view.smaller_page()
    view.next_page()
    view.more_points()
    view.zoom_in_y()

    view.reset()

    assert view.page_size is None
    assert view.page == 0
    assert view.y_window == view.full_y
    assert len(view.drawn()) == DEFAULT_POINTS


def test_zooming_y_narrows_the_values_and_stops_at_the_whole_range():
    view = graph()
    low, high = view.full_y

    view.zoom_in_y()
    assert (view.y_window[1] - view.y_window[0]) < (high - low)

    for _ in range(10):
        view.zoom_out_y()
    assert view.y_window == view.full_y


# --- marks ----------------------------------------------------------------


def marked(**kwargs):
    """A run with a mark every hundred rows, an even second apart."""
    points = [(float(i), 100.0 + i % 50) for i in range(1000)]
    marks = [(float(i), f"pulse {i // 100 + 1}") for i in range(0, 1000, 100)]
    return graph(points=points, marks=marks, **kwargs)


def test_a_mark_is_drawn_as_a_rule_across_the_picture():
    view = marked()

    assert "stroke-dasharray" in view.svg()
    assert "pulse 1" in view.svg()


def test_only_the_marks_on_this_page_are_drawn():
    """The rest are on other pages, and a rule at the edge for something
    off it would be a lie about where it is."""
    view = marked()
    view.smaller_page()

    on_page = view.marks_on_page()
    assert 0 < len(on_page) < len(view.marks)
    assert view.svg().count("stroke-dasharray") == len(on_page)


def test_a_label_that_would_collide_is_dropped_and_its_line_kept():
    """A mark whose name is unreadable under the one beside it is worse
    than a mark with no name; the line is the half that says where it
    is."""
    crowded = graph(
        points=[(float(i), 1.0 + i % 7) for i in range(1000)],
        marks=[(float(i), "a crowded label") for i in range(500, 510)],
    )
    markup = crowded.svg()

    assert markup.count("stroke-dasharray") == 10
    assert markup.count("a crowded label") < 10


# --- and moving to one ----------------------------------------------------


def test_going_to_a_mark_turns_to_the_page_holding_it():
    view = marked()
    view.smaller_page()
    view.first_page()

    view.go_to_mark(len(view.marks) - 1)

    low, high = view.x_window
    assert low <= view.marks[-1][0] <= high


def test_next_mark_steps_past_the_edge_of_this_page():
    view = marked()
    view.smaller_page()
    _start, end = view.x_window

    view.next_mark()

    low, high = view.x_window
    assert low > 0
    # It landed on the first mark that was off the right of the old page.
    assert any(end < seconds <= high for seconds, _label in view.marks_on_page())


def test_previous_mark_steps_back_the_same_way():
    view = marked()
    view.smaller_page()
    view.last_page()
    start, _end = view.x_window

    view.previous_mark()

    assert view.x_window[0] < start


def test_walking_past_the_last_mark_stays_where_it_is():
    """A control at the end of its travel does nothing, rather than
    wrapping round to the other end of the run."""
    view = marked()
    view.smaller_page()
    view.last_page()
    where = view.page

    view.next_mark()
    assert view.page == where

    view.first_page()
    view.previous_mark()
    assert view.page == 0


def test_a_mark_is_found_by_bisection_rather_than_by_reading_the_run():
    """The whole arrangement here is that nothing reads rows it will not
    draw; a linear search for a mark would read the run to find it."""
    counted = Counting([(float(i), 1.0) for i in range(4096)])
    view = graph(series=[("counted", counted)], marks=[(4000.0, "late")])
    view.smaller_page()
    view.svg()                      # let the value axis be scanned
    counted.reads = 0

    view.go_to_mark(0)

    assert counted.reads < 20       # log2(4096) is 12


def test_with_the_whole_run_on_one_page_there_is_nowhere_to_go():
    """It is already on screen. The reading says which press changes
    that, rather than leaving a link that looks broken."""
    view = marked()
    assert view.page_size is None

    view.go_to_mark(len(view.marks) - 1)

    assert view.page == 0
    reading = view._snapshot_if_opened(PATH)["marks"]["value"]
    assert "all on this page" in reading
    assert "smaller page" in reading


def test_the_reading_counts_this_page_and_the_run():
    view = marked()
    view.smaller_page()
    states = view._snapshot_if_opened(PATH)

    assert states["marks"]["value"] == (
        f"{len(view.marks_on_page())} on this page, {len(view.marks)} in all"
    )


# --- the marks node -------------------------------------------------------


def test_there_is_one_link_per_mark():
    view = marked()

    entries = view.snapshot_children["marks"].snapshot_children
    assert len(entries) == len(view.marks)
    assert all(callable(command) for command in entries.values())


def test_a_link_is_named_by_its_moment_and_its_label():
    """The time goes in front because it is what tells two marks of the
    same kind apart."""
    view = marked()

    assert "0.0s pulse 1" in view.snapshot_children["marks"].snapshot_children


def test_a_label_carrying_a_slash_does_not_become_a_path():
    """The tree splits a request on "/", so one in a key would route to a
    child that is not there."""
    view = graph(
        points=dummy_series(samples=100),
        marks=[(1.0, "male1/found")],
    )

    key, = view.snapshot_children["marks"].snapshot_children
    assert "/" not in key


def test_two_marks_at_the_same_moment_keep_separate_links():
    """One key would hide the other, and the page would offer a link that
    went to the wrong one."""
    view = graph(
        points=dummy_series(samples=100),
        marks=[(1.0, "same"), (1.0, "same")],
    )

    assert len(view.snapshot_children["marks"].snapshot_children) == 2


def test_a_graph_with_no_marks_offers_none_of_it():
    """A `marks` node listing nothing is a link to an empty page, and the
    two commands beside it could never move."""
    view = graph()

    assert "marks" not in view.snapshot_children
    assert "next mark" not in view.snapshot_children
    assert "previous mark" not in view.snapshot_children
    assert "marks" not in view._snapshot_if_opened(PATH)


def test_the_demos_marks_land_on_the_dummy_pulses():
    marks = dummy_marks()

    assert marks[0] == (0.0, "pulse 1")
    assert all(b[0] - a[0] == 47.0 for a, b in zip(marks, marks[1:]))


# --- more than one line ---------------------------------------------------


def two_lines():
    return graph(series=[
        ("female1", [(float(i), 300.0 + i) for i in range(1000)]),
        ("female2", [(float(i), 900.0 - i) for i in range(1000)]),
    ])


def test_the_value_axis_spans_every_line_rather_than_the_first():
    view = two_lines()

    low, high = view.full_y
    assert low < 300.0 and high > 900.0


def test_the_density_asked_for_is_a_density_per_line():
    """Not a budget split between them: three lines at four hundred
    points each is three readable lines, where three at a hundred and
    thirty is none."""
    view = two_lines()
    view.fewer_points()          # 200

    assert [len(points) for _, points in view.drawn_series()] == [200, 200]
    assert len(view.drawn()) == 400


def test_each_line_is_drawn_in_its_own_colour_and_named():
    markup = two_lines().svg()

    assert markup.count("<polyline") == 2
    assert "#1f77b4" in markup and "#ff7f0e" in markup
    # A legend, since with two lines which is which is the first thing
    # anybody needs to know.
    assert "female1" in markup and "female2" in markup


def test_one_unlabelled_line_keeps_the_pages_own_colour():
    """What this drew before it could hold several - and the reason a
    single line follows the theme it is drawn in rather than being told
    it is blue."""
    markup = graph().svg()

    assert 'stroke="currentColor"' in markup
    assert "#1f77b4" not in markup


def test_a_line_that_runs_out_early_is_simply_not_drawn():
    """One female whose log stops short must not take the other two off
    the picture with her. Pages are row ranges applied to every line, and
    a line with no rows in this one contributes nothing."""
    view = graph(series=[
        ("short", [(float(i), 1.0) for i in range(10)]),
        ("long", [(float(i), 2.0) for i in range(1000)]),
    ])
    view.smaller_page()          # 500 a page, so the short line is on
    view.last_page()             # page one only

    assert "nothing on this page" not in view.svg()
    assert view.svg().count("<polyline") == 1


def test_it_says_how_many_lines_it_is_drawing():
    view = two_lines()
    states = view._snapshot_if_opened(PATH)

    reading = str(states["points"]["value"])
    assert reading.startswith("2 lines:")
    assert "a line" in reading          # the density is per line


# --- a series that is a view, not a copy ----------------------------------


def test_columns_pairs_two_sequences_without_building_the_pairs():
    """What lets a run hand over its dataframe rather than a second copy
    of every reading."""
    seconds = [0.0, 1.0, 2.0]
    values = [10.0, 20.0, 30.0]
    columns = Columns(seconds, values)

    assert len(columns) == 3
    assert columns[1] == (1.0, 20.0)
    assert columns.y_range() == (10.0, 30.0)


def test_a_graph_over_columns_draws_the_same_as_over_pairs():
    points = dummy_series(samples=500)
    xs = [x for x, _ in points]
    ys = [y for _, y in points]

    assert graph(points=points).svg() == graph(points=Columns(xs, ys)).svg()


def test_columns_stops_at_the_shorter_of_the_two():
    columns = Columns([0.0, 1.0, 2.0], [5.0, 6.0])

    assert len(columns) == 2


# --- and the markup -------------------------------------------------------


def test_there_is_no_script_anywhere_in_it():
    """The whole point. It has to work with scripting off."""
    markup = graph().svg()

    assert "<script" not in markup
    assert "onclick" not in markup
    assert "javascript:" not in markup


def test_the_picture_is_drawn_from_the_page_it_says_it_is():
    view = graph()
    view.smaller_page()
    view.smaller_page()
    view.next_page()
    markup = view.svg()

    start, end = view.x_window
    assert f"{start:.1f}s" in markup
    assert f"{end:.1f}s" in markup


def test_every_control_is_a_command_the_page_can_link_to():
    """One link, one action - the tree draws a bare callable as an anchor
    through its `call` segment."""
    view = graph()

    children = view.snapshot_children
    for control in ("more points", "fewer points", "smaller page",
                    "bigger page", "first page", "previous page",
                    "next page", "last page", "zoom in y", "zoom out y",
                    "reset"):
        assert callable(children[control]), control


def test_it_says_which_page_and_how_much_of_it():
    view = graph()
    view.smaller_page()
    view.smaller_page()
    view.next_page()
    states = view._snapshot_if_opened(PATH)

    assert states["page"]["value"].startswith("page 2 of ")
    assert "on this page" in states["points"]["value"]


def test_the_whole_run_on_one_page_is_said_as_that_and_not_page_1_of_1():
    states = graph()._snapshot_if_opened(PATH)

    assert states["page"]["value"].startswith("one page - the whole of it")


def test_an_empty_page_says_so_rather_than_drawing_a_line_to_nowhere():
    view = graph(points=[(0.0, 1.0)])

    assert "nothing on this page" in view.svg()


def test_the_page_hangs_nothing_on_the_picture(renderer):
    """`image`, not `svg`. The other kind carries a `data-svg-zoom`
    handle that svg_zoom.js binds a wheel, a drag and a double-click to,
    and this view is moved by its links alone: browser-side zoom would
    scale the picture while the page stayed put, so the readings that say
    which page is drawn would name one nobody was looking at."""
    view = graph()
    states = view._snapshot_if_opened(PATH)

    assert "image" in states["graph"]
    assert "svg" not in states["graph"]

    html = renderer(states)
    assert "data-svg-zoom" not in html
    assert "scroll to zoom" not in html
    assert "<script" not in html
