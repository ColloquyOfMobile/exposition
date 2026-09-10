# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/test_virtual_panel.py

"""Putting the simulated-state column away, and getting it back.

The panel down the right of every page is a third of the width and, until
now, permanently there: `is_simulated` decided whether it existed and
nothing decided whether it was in the way. It is not a node in the tree,
so none of the tree's own open/close applied to it - it is page furniture,
drawn beside whatever is being looked at, like `refresh` and `restart`
above it.

That is the whole reason its control is a **route** rather than a command.
A tree command answers with a re-render of the node it hangs on, so the
link could only ever live on one node's page; this one has to be pressable
from every page and has to come back to the page it was pressed on. Hence
an action plus the way back, and a 303 - which is what most of these check.

Both UIs, because the panel's markup is in both and a route missing from
one of the two is exactly the drift the pair are checked against (see
CLAUDE.md). Neither is a live server here: the methods are bound onto a
double, the same trick `test_static_files.py` uses.
"""
import pytest

from colloquy.server2.wsgi2 import WSGI2
from colloquy.ui.wsgi import MockWSGI
from colloquy.virtual_drivers import VirtualDrivers

from pathlib import Path

RENDERERS = (WSGI2, MockWSGI)
IDS = ("installation", "mock")


class FakeWSGI:
    """Enough of a renderer for the route and the one link it draws."""

    def __init__(self, renderer, colloquy, base_path="app"):
        self._colloquy = colloquy
        self._root = Path("app")
        # `_base_path` is the focus's own path, relative to the app root.
        self._base_path = Path(*Path(base_path).parts[1:])
        self.log = lambda *args, **kwargs: None
        self._parse_virtual_panel = renderer._parse_virtual_panel.__get__(self)
        self._parse_not_found = renderer._parse_not_found.__get__(self)
        self._html_virtual_panel_link = (
            renderer._html_virtual_panel_link.__get__(self)
        )

    @property
    def colloquy(self):
        return self._colloquy


@pytest.fixture
def drivers(stub_factory):
    return VirtualDrivers(owner=stub_factory())


@pytest.fixture
def app(stub_factory, drivers):
    return stub_factory(is_simulated=True, virtual_drivers=drivers)


def header(headers, name):
    for key, value in headers:
        if key.lower() == name.lower():
            return value
    return None


# --- the state ----------------------------------------------------------


def test_the_panel_starts_where_it_always_was(drivers):
    """Open, which is what the page did before there was any way to shut
    it. A new control must not change what somebody sees on a first run."""
    assert drivers.panel_is_open is True


def test_it_is_not_the_nodes_own_open_and_shut(drivers):
    """Two different questions: the tree's is whether the stand-ins are
    being read right now, the panel's is whether they sit in the corner
    of the eye while something else is driven. Sharing one flag would
    mean opening the node moved a column of the page."""
    drivers.close_panel()
    drivers.open()

    assert drivers._is_opened is True
    assert drivers.panel_is_open is False

    drivers.open_panel()
    drivers.close()

    assert drivers._is_opened is False
    assert drivers.panel_is_open is True


# --- the route ----------------------------------------------------------


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_hiding_it_comes_back_to_the_page_it_was_pressed_on(
    renderer, app, drivers
):
    """The whole reason this is a route. The link is on every page, so
    pressing it three nodes deep has to answer three nodes deep."""
    status, headers, body = FakeWSGI(renderer, app)._parse_virtual_panel(
        "hide", "app", "drivers", "arduino"
    )

    assert status.startswith("303")
    assert header(headers, "Location") == "/app/drivers/arduino"
    assert body == b""
    assert drivers.panel_is_open is False


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_showing_it_again(renderer, app, drivers):
    drivers.close_panel()

    _status, headers, _body = FakeWSGI(renderer, app)._parse_virtual_panel(
        "show", "app", "tests"
    )

    assert header(headers, "Location") == "/app/tests"
    assert drivers.panel_is_open is True


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_each_verb_says_what_it_does_so_pressing_twice_is_not_a_flap(
    renderer, app, drivers
):
    """Two verbs rather than one toggle: a stale link, or a browser
    fetching one twice, then does what it says rather than whatever the
    opposite of the current state happens to be."""
    wsgi = FakeWSGI(renderer, app)
    wsgi._parse_virtual_panel("hide", "app")
    wsgi._parse_virtual_panel("hide", "app")

    assert drivers.panel_is_open is False


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_a_node_name_with_a_space_in_it_is_encoded(renderer, app):
    """Fine in an href the browser encodes for us, malformed in a header
    value - and "main pcb" is a page somebody would press this on."""
    _status, headers, _body = FakeWSGI(renderer, app)._parse_virtual_panel(
        "hide", "app", "hardware", "main pcb"
    )

    assert header(headers, "Location") == "/app/hardware/main%20pcb"


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_with_nothing_to_come_back_to_it_answers_the_front_page(renderer, app):
    _status, headers, _body = FakeWSGI(renderer, app)._parse_virtual_panel("hide")

    assert header(headers, "Location") == "/app"


# --- what it refuses ----------------------------------------------------


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_anything_but_show_or_hide_is_a_404(renderer, app, drivers):
    status, _headers, _body = FakeWSGI(renderer, app)._parse_virtual_panel(
        "sideways", "app"
    )

    assert status.startswith("404")
    assert drivers.panel_is_open is True


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_it_is_a_404_where_nothing_is_simulated(renderer, stub_factory):
    """Gated for the panel's own reason, and it matters more here:
    `Colloquy.virtual_drivers` builds the simulation on first access, so
    an installation answering this would construct nine fake servos to be
    told about a column it never draws. Reaching for the attribute at all
    fails this double."""
    app = stub_factory(is_simulated=False)

    status, _headers, _body = FakeWSGI(renderer, app)._parse_virtual_panel(
        "hide", "app"
    )

    assert status.startswith("404")


# --- the link on the page -----------------------------------------------


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_the_link_says_what_it_will_do_and_carries_the_way_back(
    renderer, app, drivers
):
    wsgi = FakeWSGI(renderer, app, base_path="app/drivers/arduino")

    shown = wsgi._html_virtual_panel_link()
    drivers.close_panel()
    hidden = wsgi._html_virtual_panel_link()

    assert 'href="/virtual-panel/hide/app/drivers/arduino"' in shown
    assert "hide virtual drivers" in shown
    assert 'href="/virtual-panel/show/app/drivers/arduino"' in hidden
    assert "show virtual drivers" in hidden
