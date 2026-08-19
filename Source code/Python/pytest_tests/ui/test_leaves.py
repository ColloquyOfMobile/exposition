"""Unit tests for colloquy.ui.leaves - the vocabulary the object tree and
the web UI share.

Two halves, and the second is the point of the module existing:

1. the constructors build what they say they build;
2. every kind they can build is a kind the renderer actually draws.

That second half is the first test in this suite to render HTML. It
builds a snapshot dict by hand and hands it to _html_recursion with no
Colloquy object, no hardware and no request - which is possible because
the renderer only ever reads dicts. It is constructed through __new__ on
purpose: __init__ parses a whole request, and none of that is needed to
draw a leaf. If that ever stops working, the renderer has grown a
dependency on the tree that this suite is meant to keep out of it.

There are two renderers while the page is being rebuilt - the
installation's (server2/wsgi2.py) and the mock's (ui/wsgi.py) - and every
test below runs against both. They are free to diverge in how a page
looks; what they may not do is stop drawing a kind the vocabulary offers.
"""
from pathlib import Path

import pytest

from colloquy.server2.wsgi2 import WSGI2
from colloquy.ui.wsgi import MockWSGI
from colloquy.ui import leaves

PATH = ("hardware", "female1", "angle")


@pytest.fixture(params=(WSGI2, MockWSGI), ids=("installation", "mock"))
def render(request):
    """The HTML one of the two pages would draw for an opened node."""
    renderer_class = request.param

    def render_with(states):
        renderer = renderer_class.__new__(renderer_class)
        renderer._base_path = Path("hardware")
        renderer._root = Path("app")
        obj = {"path": PATH, "name": "angle", "opened": True, **states}
        return renderer._html_recursion(obj)

    return render_with


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


def test_a_value_is_drawn_as_key_and_reading(render):
    html = render({"angle": leaves.value(PATH, "angle", "29.3 deg")})

    assert "angle: 29.3 deg" in html


def test_html_is_dropped_in_as_it_is(render):
    html = render({"rendered": leaves.html(PATH, "rendered", "<p>a table</p>")})

    assert "<p>a table</p>" in html


def test_pre_keeps_its_text(render):
    html = render({"content": leaves.pre(PATH, "content", "line one\nline two")})

    assert "<pre" in html
    assert "line one" in html


def test_svg_is_inlined_with_its_pan_and_zoom_handle(render):
    html = render({"picture": leaves.svg(PATH, "picture", "<svg id='x'/>")})

    assert "<svg id='x'/>" in html
    assert "data-svg-zoom" in html


def test_a_chart_ships_its_data_to_the_browser(render):
    html = render({"graph": leaves.chart(PATH, "graph", '{"data": [[1], [2]]}')})

    assert "colloquyRenderChart" in html
    assert '{"data": [[1], [2]]}' in html


def test_an_editor_is_a_textarea_posting_to_the_nodes_save(render):
    html = render({"editor": leaves.editor(PATH, "editor", "some text")})

    assert "<textarea" in html
    assert "some text" in html
    # Posts to the node's own save command - the node has to register one.
    assert "/app/hardware/call/female1/angle/save" in html


@pytest.mark.parametrize("kind", leaves.KINDS)
def test_the_renderer_draws_every_kind_the_vocabulary_offers(kind, render):
    # The contract, in one line: a kind nobody can draw has no business
    # being a kind. Anything unhandled falls through to the node branch,
    # which reads value["path"] and draws an open-arrow for something
    # that cannot be opened.
    payload = "{}" if kind == "chart" else "payload"
    html = render({"some key": leaves.leaf(PATH, "some key", kind, payload)})

    assert "some key" in html or "payload" in html
    # The give-away of the fall-through: an open link for a leaf.
    assert "/open" not in html
