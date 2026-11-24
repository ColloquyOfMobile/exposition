"""The page keeps itself current: `/live` and the commands in flight.

See `ui/live.py` and `ui/in_flight.py`. The stream is driven here by hand
- one `next()` at a time, with the server's stop event set to end it -
so nothing waits on a real clock for longer than a tick.
"""
import itertools
import threading
from threading import Event, Lock
from types import SimpleNamespace

from colloquy.ui import live
from colloquy.ui.in_flight import IN_FLIGHT, InFlight, command_of
from colloquy.ui.mock import MockApp, OfflineServer, request
from colloquy.ui.wsgi import MockWSGI


def _open(path, app=None, last_event_id=None, query=""):
    server = OfflineServer(app=app or MockApp())
    environ = {"PATH_INFO": path, "REQUEST_METHOD": "GET", "QUERY_STRING": query}
    if last_event_id:
        environ["HTTP_LAST_EVENT_ID"] = last_event_id
    answers = []
    response = MockWSGI(server, environ, lambda *args: answers.append(args))
    return server, answers, iter(response)


def _events(chunks, server, count):
    """The next `count` events (heartbeats and the retry line skipped)."""
    found = []
    for chunk in chunks:
        text = chunk.decode()
        if text.startswith("event: "):
            found.append(text)
            if len(found) == count:
                break
    server.shutdown_event.set()
    list(chunks)
    return found


def _revision_of(page):
    return page.split('data-revision="', 1)[1].split('"', 1)[0]


def test_the_page_no_longer_offers_refresh_values():
    _, page = request("/app/readings")
    assert "Refresh values" not in page
    assert 'id="live-status"' in page
    assert _revision_of(page)


def test_the_stream_sends_the_tree_the_page_would_draw():
    app = MockApp()
    _, page = request("/app/documents", app=app)
    server, answers, chunks = _open("/live/app/documents", app=app)
    assert next(chunks).startswith(b"retry: ")
    commands, tree = _events(chunks, server, 2)
    assert answers[0][0] == "200 OK"
    assert ("Content-Type", "text/event-stream; charset=utf-8") in answers[0][1]
    assert commands.startswith("event: commands\n")
    assert tree.startswith("event: tree\n")
    assert f"id: {_revision_of(page)}\n" in tree
    body = page.split('data-revision="', 1)[1].split(">", 1)[1]
    first_line = tree.split("data: ", 1)[1].split("\n", 1)[0]
    assert first_line in body


def test_a_page_that_is_current_is_sent_nothing_and_a_reconnect_says_what_it_holds():
    app = MockApp()
    revision = _revision_of(request("/app/documents", app=app)[1])
    for kwargs in ({"query": f"revision={revision}"}, {"last_event_id": revision}):
        server, _, chunks = _open("/live/app/documents", app=app, **kwargs)
        found = []
        for _ in range(6):
            found.append(next(chunks).decode())
        server.shutdown_event.set()
        list(chunks)
        assert not any(text.startswith("event: tree") for text in found)


def test_the_stream_never_runs_a_command_and_answers_a_missing_node_with_gone():
    server, answers, chunks = _open("/live/app/buttons/call/press")
    list(chunks)
    assert answers[0][0].startswith("404")
    server, _, chunks = _open("/live/app/no such node")
    assert next(chunks).startswith(b"retry")
    assert _events(chunks, server, 2)[-1].startswith("event: gone")


def test_a_held_command_lock_is_never_waited_on():
    """While a command holds the lock, ticks skip the render."""
    lock = Lock()
    rendered = []

    def render():
        if not lock.acquire(timeout=0):
            return live.BUSY
        try:
            rendered.append(True)
            return ("tree", "<div></div>", "r1")
        finally:
            lock.release()

    stop = Event()
    lock.acquire()
    chunks = live.stream(render, stop, in_flight=InFlight())
    next(chunks)  # retry
    next(chunks)  # commands
    timer = threading.Timer(0.6, stop.set)
    timer.start()
    leftover = list(chunks)
    lock.release()
    assert rendered == []
    assert not any(chunk.startswith(b"event: tree") for chunk in leftover)


def test_a_render_that_raises_is_reported_once_and_cleared():
    outcomes = iter([("trouble", "boom"), ("trouble", "boom"), ("tree", "<p>", "r2")])
    stop = Event()
    stop.wait = lambda timeout: None  # the clock below is the only time
    clock = itertools.count(0, 2)
    chunks = live.stream(lambda: next(outcomes), stop, in_flight=InFlight(),
                         clock=lambda: next(clock))
    seen = []
    for chunk in chunks:
        if chunk.startswith(b"event: "):
            seen.append(chunk)
        if len(seen) == 4:
            break
    assert seen[1:] == [
        live.event("trouble", "boom"),  # once, though raised twice
        live.event("trouble"),
        live.event("tree", "<p>", "r2"),
    ]


def test_the_board_out_ends_the_stream():
    pcb = SimpleNamespace(is_mounted=False)
    root = SimpleNamespace(hardware=SimpleNamespace(main_pcb=pcb))
    from colloquy.server2.wsgi2 import WSGI2
    server = OfflineServer(root)
    answers = []
    response = WSGI2(server, {"PATH_INFO": "/live/app"}, lambda *args: answers.append(args))
    chunks = [chunk.decode() for chunk in response]
    assert answers[0][0] == "200 OK"
    assert chunks[-1].startswith("event: gone")


# --- commands in flight ---------------------------------------------------


def test_a_command_is_named_the_same_from_every_page():
    assert command_of(("drivers", "call", "female1", "home")) == "drivers/female1/home"
    assert command_of(("drivers", "female1", "call", "home")) == "drivers/female1/home"


def test_a_press_is_queued_then_running_then_gone():
    board = InFlight()
    with board.pressed("buttons/press"):
        assert [entry["state"] for entry in board.snapshot()] == ["queued"]
        board.started()
        assert [entry["state"] for entry in board.snapshot()] == ["running"]
    assert board.snapshot() == []
    board.started()  # nobody pressed anything on this thread
    assert board.snapshot() == []


def test_the_walk_marks_a_press_running_while_its_command_runs():
    app = MockApp()
    seen = []
    original = app._buttons.snapshot

    def watching(*args, **kwargs):
        state = original(*args, **kwargs)
        for key, value in list(state.items()):
            if callable(value):
                def spy(*a, _value=value, **k):
                    seen.append(IN_FLIGHT.snapshot())
                    return _value(*a, **k)
                state[key] = spy
        return state

    app._buttons.snapshot = watching
    _, page = request("/app/buttons", app=app)
    command = page.split('href="/app/buttons/call/', 1)[1].split('"', 1)[0]
    request(f"/app/buttons/call/{command}", app=app)
    assert seen and seen[0] == [
        {"command": f"buttons/{command}", "state": "running", "seconds": seen[0][0]["seconds"]}
    ]
    assert IN_FLIGHT.snapshot() == []
