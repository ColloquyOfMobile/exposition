"""Unit tests for colloquy.ui.leaves - the vocabulary the object tree and
the web UI share.

Two halves, and the second is the point of the module existing:

1. the constructors build what they say they build;
2. every kind they can build is a kind the renderer actually draws.

That second half is the first test in this suite to render HTML. It
builds a snapshot dict by hand and hands it to WSGI2._html_recursion with
no Colloquy object, no hardware and no request - which is possible because
the renderer only ever reads dicts. It is constructed through __new__ on
purpose: WSGI2.__init__ parses a whole request, and none of that is
needed to draw a leaf. If that ever stops working, the renderer has grown
a dependency on the tree that this suite is meant to keep out of it.
"""
from pathlib import Path

import pytest

from colloquy.server2.wsgi2 import WSGI2
from colloquy.ui import leaves

PATH = ("hardware", "female1", "angle")


def render(states):
    """The HTML the page would draw for one opened node's snapshot."""
    renderer = WSGI2.__new__(WSGI2)
    renderer._base_path = Path("hardware")
    renderer._root = Path("app")
    obj = {"path": PATH, "name": "angle", "opened": True, **states}
    return renderer._html_recursion(obj)


# --- the constructors ----------------------------------------------------


def test_a_leaf_is_its_path_its_name_and_its_kind():
    assert leaves.value(PATH, "goal", "29.3") == {
        "path": PATH + ("goal",),
        "name": "goal",
        "value": "29.3",
    }


def test_the_key_names_the_kind():
    assert "html" in leaves.html(PATH, "rendered", "<p>hi</p>")
    assert "chart" in leaves.chart(PATH, "graph", "{}")
    assert "svg" in leaves.svg(PATH, "picture", "<svg/>")
    assert "pre" in leaves.pre(PATH, "log", "a line")
    assert "editor" in leaves.editor(PATH, "editor", "text")


def test_every_constructor_names_the_leaf_after_its_key():
    # The page shows the dict key, so a name that disagrees with it only
    # ever misleads whoever reads the snapshot. One node did disagree.
    for build in (leaves.value, leaves.html, leaves.chart, leaves.svg, leaves.pre):
        leaf = build(PATH, "some key", "payload")
        assert leaf["name"] == "some key"
        assert leaf["path"] == PATH + ("some key",)


def test_an_unknown_kind_is_refused_where_it_is_written():
    # Rather than in the browser, as a dict printed where a reading should
    # be - which is how a mistyped kind used to show up.
    with pytest.raises(AssertionError):
        leaves.leaf(PATH, "x", "gauge", 1)


def test_into_files_value_leaves_under_one_path():
    states = {}
    leaf = leaves.into(states, PATH)

    leaf("angle", "29.3")
    leaf("goal", "30.0")

    assert states == {
        "angle": leaves.value(PATH, "angle", "29.3"),
        "goal": leaves.value(PATH, "goal", "30.0"),
    }


def test_into_returns_the_leaf_it_filed():
    states = {}
    leaf = leaves.into(states, PATH)

    assert leaf("angle", "29.3") is states["angle"]


# --- the renderer draws every kind ---------------------------------------


def test_a_value_is_drawn_as_key_and_reading():
    html = render({"angle": leaves.value(PATH, "angle", "29.3 deg")})

    assert "angle: 29.3 deg" in html


def test_html_is_dropped_in_as_it_is():
    html = render({"rendered": leaves.html(PATH, "rendered", "<p>a table</p>")})

    assert "<p>a table</p>" in html


def test_pre_keeps_its_text():
    html = render({"content": leaves.pre(PATH, "content", "line one\nline two")})

    assert "<pre" in html
    assert "line one" in html


def test_svg_is_inlined_with_its_pan_and_zoom_handle():
    html = render({"picture": leaves.svg(PATH, "picture", "<svg id='x'/>")})

    assert "<svg id='x'/>" in html
    assert "data-svg-zoom" in html


def test_a_chart_ships_its_data_to_the_browser():
    html = render({"graph": leaves.chart(PATH, "graph", '{"data": [[1], [2]]}')})

    assert "colloquyRenderChart" in html
    assert '{"data": [[1], [2]]}' in html


def test_an_editor_is_a_textarea_posting_to_the_nodes_save():
    html = render({"editor": leaves.editor(PATH, "editor", "some text")})

    assert "<textarea" in html
    assert "some text" in html
    # Posts to the node's own save command - the node has to register one.
    assert "/app/hardware/call/female1/angle/save" in html


# One sample per kind. A new kind has to be added here, which is the
# point: the test below then makes sure the renderer grew a branch for it.
SAMPLES = {
    "value": lambda: leaves.value(PATH, "some key", "payload"),
    "editable": lambda: leaves.editable(PATH, "some key", "payload"),
    "editor": lambda: leaves.editor(PATH, "some key", "payload"),
    "html": lambda: leaves.html(PATH, "some key", "<p>payload</p>"),
    "chart": lambda: leaves.chart(PATH, "some key", "{}"),
    "pre": lambda: leaves.pre(PATH, "some key", "payload"),
    "svg": lambda: leaves.svg(PATH, "some key", "<svg/>"),
}


@pytest.mark.parametrize("kind", leaves.KINDS)
def test_the_renderer_draws_every_kind_the_vocabulary_offers(kind):
    # The contract, in one test: a kind nobody can draw has no business
    # being a kind. An unhandled kind falls through to the node branch,
    # which draws an open-arrow for something that cannot be opened.
    assert kind in SAMPLES, f"{kind} needs a sample here"

    html = render({"some key": SAMPLES[kind]()})

    assert "some key" in html or "payload" in html
    # The give-away of the fall-through: an open link for a leaf.
    assert "/open" not in html


def test_an_editable_leaf_draws_a_box_posting_to_the_nodes_command():
    html = render({"angle": leaves.editable(PATH, "angle", 29.3, hint="degrees")})

    assert "angle: 29.3" in html
    assert 'value="29.3"' in html
    assert "degrees" in html
    # The node this leaf belongs to, and the command it registered.
    assert 'action="/app/hardware/call/female1/angle/commit"' in html


def test_an_editable_leaf_can_name_another_command():
    html = render({"x": leaves.editable(PATH, "x", 1, command="set_it")})

    assert "/call/female1/angle/set_it" in html
