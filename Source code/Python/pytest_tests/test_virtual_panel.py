"""Compatibility for bookmarks made before simulation moved into the tree."""
from types import SimpleNamespace

import pytest

from colloquy.server2.wsgi2 import WSGI2
from colloquy.ui.wsgi import MockWSGI


@pytest.fixture(params=[WSGI2, MockWSGI])
def page(request):
    obj = request.param.__new__(request.param)
    obj._colloquy = SimpleNamespace(is_simulated=True)
    obj._parse_not_found = lambda *args: ("404 Not Found", [], b"")
    return obj


@pytest.mark.parametrize(("args", "destination"), [
    (("show", "app", "tests"), "/app/simulation"),
    (("hide", "app", "hardware", "main pcb"), "/app/hardware/main%20pcb"),
    (("hide",), "/app"),
    (("hide", "app", "drivers", "call", "start"), "/app"),
    (("hide", "shutdown"), "/app"),
])
def test_old_panel_links_lead_to_nodes(page, args, destination):
    status, headers, body = page._parse_virtual_panel(*args)
    assert status.startswith("303")
    assert dict(headers)["Location"] == destination
    assert body == b""


def test_the_real_installation_never_opens_the_simulation(page):
    page.colloquy.is_simulated = False
    assert page._parse_virtual_panel("show")[0].startswith("404")


@pytest.mark.parametrize("args", [(), ("sideways",)])
def test_unknown_panel_actions_are_missing(page, args):
    assert page._parse_virtual_panel(*args)[0].startswith("404")
