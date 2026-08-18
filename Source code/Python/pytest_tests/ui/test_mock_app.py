"""Tests for the UI, driven against colloquy.ui.mock instead of the
installation.

This is what the mock exists for: whole pages, through the real request
parsing and the real renderer, with no Colloquy object, no hardware, no
threads and no socket. A page here costs about 3KB and a millisecond,
against 16-86KB and a second of servo reads for the real tree.

If something in here needs a body, a servo or a thread to be exercised,
it does not belong in this file - it belongs against the real classes, or
in a scenario under colloquy/tests/.
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


def test_a_command_that_raises_is_not_swallowed(app):
    # It reaches the server, which treats it as a crash - the behaviour
    # this button exists to make visible. Here it is only an exception.
    with pytest.raises(RuntimeError):
        request("/app/buttons/call/fail on purpose", app=app)


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


def test_an_emergency_stop_leaves_the_page_reachable(app):
    server = OfflineServer(app=app)

    request("/emergency-stop", server=server)

    assert "emergency_stop" in app.called
    # Unlike /shutdown: the server stays up so the page can still be used.
    assert not server.shutdown_event.is_set()
