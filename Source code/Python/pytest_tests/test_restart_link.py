# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/test_restart_link.py

"""`restart`, and the `reload` it answers with, coming back to the page.

The restart page's only content is a `reload` link, and it pointed at `/`
whatever page `restart` had been pressed on - so restarting to pick up a
change meant walking back down to the node being worked on, every time.
The link at the top of every page now carries that page's app path after
`/restart/`, the shape `/virtual-panel/` already uses, and `reload` goes
there.

Both UIs, for `test_virtual_panel.py`'s reason. Neither is a live server
and nothing is re-executed: the methods are bound onto a double whose
`colloquy` only records being shut down.
"""
import pytest

from colloquy.server2.wsgi2 import WSGI2
from colloquy.ui.wsgi import MockWSGI

from pathlib import Path
from threading import Event

RENDERERS = (WSGI2, MockWSGI)
IDS = ("installation", "mock")


class FakeColloquy:
    def __init__(self):
        self.calls = []

    def shutdown(self):
        self.calls.append("shutdown")

    def join_all(self):
        self.calls.append("join_all")


class FakeWSGI:
    """Enough of a renderer for the route and the one link it draws."""

    def __init__(self, renderer, base_path="app"):
        self.colloquy = FakeColloquy()
        self.shutdown_event = Event()
        self.restart_event = Event()
        self._root = Path("app")
        # `_base_path` is the focus's own path, relative to the app root.
        self._base_path = Path(*Path(base_path).parts[1:])
        self._parse_restart = renderer._parse_restart.__get__(self)
        self._html_restart_link = renderer._html_restart_link.__get__(self)


# --- the link on the page -----------------------------------------------


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_the_link_carries_the_page_it_is_on(renderer):
    html = FakeWSGI(renderer, "app/drivers/arduino")._html_restart_link()

    assert 'href="/restart/app/drivers/arduino"' in html
    assert ">restart<" in html


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_on_the_front_page_it_carries_the_front_page(renderer):
    html = FakeWSGI(renderer, "app")._html_restart_link()

    assert 'href="/restart/app"' in html


# --- the route ----------------------------------------------------------


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_reload_comes_back_to_where_restart_was_pressed(renderer):
    wsgi = FakeWSGI(renderer)
    status, _headers, body = wsgi._parse_restart("app", "drivers", "arduino")

    assert status.startswith("200")
    assert b'href="/app/drivers/arduino"' in body
    assert b">reload<" in body


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_it_still_restarts(renderer):
    """Where the reload goes changes nothing about what the restart does."""
    wsgi = FakeWSGI(renderer)
    wsgi._parse_restart("app", "tests")

    assert wsgi.colloquy.calls == ["shutdown", "join_all"]
    assert wsgi.shutdown_event.is_set()
    assert wsgi.restart_event.is_set()


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_a_node_name_with_a_space_in_it_is_encoded(renderer):
    """`_parse_path` unquoted it on the way in, so it is quoted back."""
    _status, _headers, body = FakeWSGI(renderer)._parse_restart(
        "app", "hardware", "main pcb"
    )

    assert b'href="/app/hardware/main%20pcb"' in body


@pytest.mark.parametrize("renderer", RENDERERS, ids=IDS)
def test_with_nothing_to_come_back_to_it_is_the_front_page(renderer):
    """The emergency-stop page's `restart` carries no page, and neither
    does a typed `/restart` - both reload to `/`, as before."""
    _status, _headers, body = FakeWSGI(renderer)._parse_restart()

    assert b'href="/"' in body
