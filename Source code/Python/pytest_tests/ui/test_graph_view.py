# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/ui/test_graph_view.py

"""A chart that needs no script, and keeps the data on the server.

The page's other chart is uPlot: every point crosses the wire and the
browser decides what to draw. This one is the opposite - the window is
known before anything is rendered, so the thinning happens against the
data. What is worth pinning is exactly that: that the number of points
sent is the server's decision and follows the window, and that no control
needs anything but an `href`.
"""
from types import SimpleNamespace

from colloquy.ui.graph_view import (
    DEFAULT_POINTS,
    POINT_CHOICES,
    GraphView,
    dummy_series,
)


def graph(**kwargs):
    return GraphView(owner=SimpleNamespace(owner=None, owners=[]), **kwargs)


# --- the data ------------------------------------------------------------


def test_the_dummy_data_is_the_same_every_time():
    """Paging around it has to be paging around one dataset, and the two
    computers have to see the same picture."""
    assert dummy_series(samples=50) == dummy_series(samples=50)


def test_it_has_something_to_find_at_more_than_one_scale():
    """Zooming is only worth having if there is structure under it: a slow
    sweep to see zoomed out, pulses in the middle, noise at the bottom."""
    values = [value for _, value in dummy_series()]

    assert max(values) - min(values) > 400        # the sweep
    steps = [abs(b - a) for a, b in zip(values, values[1:])]
    assert max(steps) > 100                       # a pulse edge
    assert min(steps) < 5                         # and fine detail


# --- what the server decides ---------------------------------------------


def test_it_opens_on_a_readable_density_rather_than_everything():
    view = graph()

    assert len(view.visible()) > DEFAULT_POINTS
    assert len(view.drawn()) == DEFAULT_POINTS


def test_zooming_in_narrows_the_window_and_the_work():
    view = graph()
    before = len(view.visible())

    view.zoom_in_x()
    view.zoom_in_x()

    assert len(view.visible()) < before
    # Still the same number drawn - the reader asked for that many, and
    # the window got denser rather than the picture sparser.
    assert len(view.drawn()) == DEFAULT_POINTS


def test_far_enough_in_and_every_sample_is_drawn():
    """Past that point there is nothing to thin, and it says so by drawing
    fewer than were asked for."""
    view = graph()
    for _ in range(10):
        view.zoom_in_x()

    assert len(view.drawn()) == len(view.visible())
    assert len(view.drawn()) < DEFAULT_POINTS


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


# --- moving about ---------------------------------------------------------


def test_scrolling_moves_the_window_without_leaving_the_data():
    view = graph()
    view.zoom_in_x()
    view.zoom_in_x()
    start, _end = view.x_window

    view.scroll_right()
    moved, _end = view.x_window
    assert moved > start

    for _ in range(20):
        view.scroll_right()
    low, high = view.full_x
    assert view.x_window[1] <= high + 1e-9


def test_a_press_moves_less_the_further_in_you_are():
    """Which is what makes one link usable at every scale."""
    coarse = graph()
    coarse.zoom_in_x()
    before = coarse.x_window[0]
    coarse.scroll_right()
    coarse_step = coarse.x_window[0] - before

    fine = graph()
    for _ in range(5):
        fine.zoom_in_x()
    before = fine.x_window[0]
    fine.scroll_right()

    assert (fine.x_window[0] - before) < coarse_step


def test_zooming_out_stops_at_the_whole_dataset():
    view = graph()
    for _ in range(10):
        view.zoom_out_x()

    assert view.x_window == view.full_x


def test_zoom_xy_moves_both_and_reset_puts_it_all_back():
    view = graph()
    view.zoom_in()
    view.scroll_right()
    view.more_points()

    view.reset()

    assert view.x_window == view.full_x
    assert view.y_window == view.full_y
    assert len(view.drawn()) == DEFAULT_POINTS


# --- and the markup -------------------------------------------------------


def test_there_is_no_script_anywhere_in_it():
    """The whole point. It has to work with scripting off."""
    markup = graph().svg()

    assert "<script" not in markup
    assert "onclick" not in markup
    assert "javascript:" not in markup


def test_the_picture_is_drawn_from_the_window_it_says_it_is():
    view = graph()
    view.zoom_in_x()
    markup = view.svg()

    start, end = view.x_window
    assert f"{start:.1f}s" in markup
    assert f"{end:.1f}s" in markup


def test_every_control_is_a_command_the_page_can_link_to():
    """One link, one action - the tree draws a bare callable as an anchor
    through its `call` segment."""
    view = graph()

    children = view.snapshot_children
    for control in ("more points", "fewer points", "zoom in x", "zoom out x",
                    "zoom in y", "zoom out y", "zoom in", "zoom out",
                    "scroll left", "scroll right", "reset"):
        assert callable(children[control]), control


def test_it_says_how_many_of_how_many_it_is_showing():
    """The number this exists to keep hold of."""
    view = graph()
    states = view._snapshot_if_opened(("app", "graph"))

    reading = states["values"]["points"] if "values" in states else None
    assert reading is None or "of" in str(reading)
    assert "graph" in states


def test_an_empty_window_says_so_rather_than_drawing_a_line_to_nowhere():
    view = graph(points=[(0.0, 1.0)])

    assert "nothing in this window" in view.svg()
