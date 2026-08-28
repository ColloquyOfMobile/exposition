"""Tests for the UI, driven against colloquy.ui.mock instead of the
installation.

This is what the mock exists for: whole pages, through the real request
parsing and the real renderer, with no Colloquy object, no hardware, no
threads and no socket. A page here costs about 3KB and a millisecond,
against 16-86KB and a second of servo reads for the real tree.

If something in here needs a body, a servo or a thread to be exercised,
it does not belong in this file - it belongs against the real classes, or
in a hardware test under colloquy/tests/.
"""
import pytest

from colloquy.ui.mock import MockApp, OfflineServer, request


@pytest.fixture
def app():
    return MockApp()


PAGES = (
    "/app",
    "/app/readings",
    "/app/buttons",
    "/app/documents",
    "/app/documents/notes",
    "/app/pictures",
    "/app/deep",
    "/app/deep/deep again",
    "/app/deep/deep again/deep again again",
)


@pytest.mark.parametrize("page", PAGES)
def test_every_page_of_the_mock_renders(page, app):
    status, html = request(page, app=app)

    assert status == "200 OK"
    assert "<!DOCTYPE html>" in html


def test_the_root_lists_its_children(app):
    _status, html = request("/app", app=app)

    for name in ("readings", "buttons", "documents", "pictures", "deep"):
        assert name in html


def test_a_reading_is_drawn(app):
    _status, html = request("/app/readings", app=app)

    assert "a number: 42" in html
    assert "with a unit: 29.3 deg" in html


def test_the_page_is_drawn_from_the_tree_every_time(app):
    # The counter increments as the node is drawn, so a page that showed
    # the same number twice would mean something is being cached between
    # requests.
    _status, first = request("/app/readings", app=app)
    _status, second = request("/app/readings", app=app)

    assert "times drawn: 1" in first
    assert "times drawn: 2" in second


def test_a_command_is_a_link_that_calls_it(app):
    _status, html = request("/app/buttons", app=app)
    assert "said: nothing" in html
    assert "/app/buttons/call/say hello" in html

    _status, html = request("/app/buttons/call/say hello", app=app)

    assert "said: hello" in html


def test_a_command_that_raises_draws_a_page_and_keeps_the_server(app):
    """What this button exists to make visible, and it changed.

    It used to reach the server's catch-all, which treats any unhandled
    exception as a fault worth taking everything down - and on the
    installation, worth an emergency stop. Twice in two days that cost
    the whole server over a fault with a page-sized answer (a board on
    last month's sketch, a COM number remembered from another machine),
    so a *command* that raises is now drawn instead. The limit is
    pinned in pytest_tests/test_command_failed_page.py: anything raised
    outside a command still propagates.
    """
    status, html = request("/app/buttons/call/fail on purpose", app=app)

    assert status == "200 OK"
    assert "fail on purpose failed." in html
    assert "RuntimeError: this command always fails" in html
    # And a way back that does not run it again.
    assert 'href="/app/buttons"' in html


def test_the_document_page_carries_both_formatted_kinds(app):
    _status, html = request("/app/documents", app=app)

    assert "<h3>A rendered document</h3>" in html
    assert "12:00:01 first line" in html


def test_the_pictures_page_carries_both_drawn_kinds(app):
    _status, html = request("/app/pictures", app=app)

    assert "an svg" in html
    assert "colloquyRenderChart" in html


def test_an_editor_saves_what_is_posted_to_it(app):
    status, html = request("/app/documents/notes", app=app)
    assert "Type something and press save." in html

    status, _html = request(
        "/app/documents/notes/call/save", app=app, content="rewritten"
    )

    assert status.startswith("303")
    _status, html = request("/app/documents/notes", app=app)
    assert "rewritten" in html


def test_a_path_that_leads_nowhere_is_not_found(app):
    status, html = request("/app/readings/nowhere", app=app)

    assert status.startswith("404")
    assert "nowhere" in html


def test_shutdown_asks_the_application_to_stop(app):
    server = OfflineServer(app=app)

    request("/shutdown", server=server)

    # The order the route does it in: stop the threads, then make the
    # hardware safe.
    assert app.called == [
        "shutdown",
        "join_all",
        "shutdown_neopixels",
        "move_to_origin",
        "disable_torque",
    ]
    assert server.shutdown_event.is_set()


def test_restart_stops_the_application_and_asks_for_a_restart(app):
    # What comes back is decided by Server2.restart_process(), which
    # re-execs sys.argv - so mock_ui.py comes back as mock_ui.py. It used
    # to re-exec "main.py colloquy1" whatever had been run, so restarting
    # the mock handed you the installation on another port.
    server = OfflineServer(app=app)

    request("/restart", server=server)

    assert app.called == ["shutdown", "join_all"]
    assert server.shutdown_event.is_set()
    assert server.restart_event.is_set()


def test_the_mock_offers_no_emergency_stop(app):
    # It belongs to an application with servos to cut torque on. Here it
    # would be a button that lies, so the page leaves it out.
    _status, html = request("/app", app=app)

    assert "EMERGENCY STOP" not in html
    assert "/emergency-stop" not in html


def test_the_emergency_stop_route_refuses_where_there_is_no_hardware(app):
    # Reachable by a stale link or a typed URL even when the page does
    # not offer it.
    server = OfflineServer(app=app)

    status, _html = request("/emergency-stop", server=server)

    assert status.startswith("404")
    assert app.called == []
    assert not server.shutdown_event.is_set()
