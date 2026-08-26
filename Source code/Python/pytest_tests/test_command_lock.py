"""One command at a time, now that the server answers several requests
at once.

The server used to serve strictly serially, which was an accidental lock
around the whole application. `Colloquy.get_states` holds a real one in
its place, and these pin the three things that arrangement is for:

1. the command really does run inside the lock (not merely beside it);
2. `hold_commands` waits for it, and gives up rather than waiting for
   ever - a shutdown held off indefinitely by a stuck command would be
   worse than one that overlaps it;
3. the threaded server's close-time defaults are the ones the shutdown
   path relies on.

No Colloquy is built (see conftest) - `get_states` and `hold_commands`
are called unbound against a double holding a real Lock, which is the
only part of the object either of them touches.
"""
import socketserver
from threading import Lock, Thread
from time import sleep

import pytest

from colloquy import COMMAND_WAIT, Colloquy
from colloquy.server2 import ThreadingWSGIServer


class Double:
    """Everything `get_states` and `hold_commands` touch, and no more."""

    def __init__(self):
        self._command_lock = Lock()


def test_the_walk_runs_inside_the_lock(monkeypatch):
    """The point of the lock, and the thing a stray refactor would undo:
    it is not enough for the lock to exist, the walk has to be under it."""
    from colloquy.ui import tree

    double = Double()
    seen = []

    def walk(root, *args):
        seen.append(double._command_lock.locked())
        return "states"

    monkeypatch.setattr(tree, "get_states", walk)

    assert Colloquy.get_states(double, "drivers") == "states"
    assert seen == [True]
    # And released afterwards, or the second page request would hang.
    assert double._command_lock.locked() is False


def test_the_lock_is_released_when_a_command_raises(monkeypatch):
    """A command that raises is not unusual here - an unknown path raises
    NotImplementedError by design. Holding the lock through it would wedge
    every later request."""
    from colloquy.ui import tree

    double = Double()

    def explodes(root, *args):
        raise NotImplementedError("no such node")

    monkeypatch.setattr(tree, "get_states", explodes)

    try:
        Colloquy.get_states(double, "nonsense")
    except NotImplementedError:
        pass

    assert double._command_lock.locked() is False


# --- hold_commands --------------------------------------------------------


def test_hold_commands_takes_the_lock_and_says_it_held_it():
    double = Double()
    with Colloquy.hold_commands(double) as held:
        assert held is True
        assert double._command_lock.locked() is True
    assert double._command_lock.locked() is False


def test_hold_commands_waits_for_a_command_already_running():
    """What /shutdown wants: let the command in flight finish before
    homing every body and cutting torque."""
    double = Double()
    double._command_lock.acquire()

    def release_shortly():
        sleep(0.2)
        double._command_lock.release()

    releaser = Thread(target=release_shortly)
    releaser.start()
    try:
        with Colloquy.hold_commands(double, timeout=5.0) as held:
            assert held is True
    finally:
        releaser.join()


def test_hold_commands_gives_up_rather_than_waiting_for_ever():
    """A command can legitimately sit for a minute (wait_for_servo's own
    timeout is 60s). A shutdown that could be blocked indefinitely by one
    would be worse than a shutdown that overlaps it, so the block runs
    either way and `held` says which happened."""
    double = Double()
    double._command_lock.acquire()
    try:
        with Colloquy.hold_commands(double, timeout=0.05) as held:
            assert held is False
    finally:
        double._command_lock.release()


def test_a_failed_hold_does_not_release_a_lock_it_never_took():
    """The bug this shape avoids: releasing on the way out of a block
    that never acquired would free the lock out from under whichever
    thread does hold it."""
    double = Double()
    double._command_lock.acquire()

    with Colloquy.hold_commands(double, timeout=0.05) as held:
        assert held is False

    # Still held by the original acquirer, not released by the block.
    assert double._command_lock.locked() is True
    double._command_lock.release()


def test_the_shutdown_wait_is_bounded_and_generous():
    # Long enough for an ordinary command, far short of wait_for_servo's
    # own 60s timeout - the point is to not wait for a stuck one.
    assert 1.0 <= COMMAND_WAIT <= 30.0


# --- the threaded server --------------------------------------------------


def test_the_server_runs_a_thread_per_connection():
    assert issubclass(ThreadingWSGIServer, socketserver.ThreadingMixIn)


def test_in_flight_requests_are_joined_before_the_socket_closes():
    """/shutdown sets the event from a worker thread while the accept loop
    is already back in accept(). These two defaults are what make its
    goodbye finish being written before server_close() pulls the socket -
    they are inherited rather than set, so this is here to notice if a
    later edit sets them."""
    assert ThreadingWSGIServer.daemon_threads is False
    assert ThreadingWSGIServer.block_on_close is True


# --- the crash handler, which must not crash -----------------------------


class _Boom(Exception):
    """The original crash, the one that must survive being handled."""


def _server_double(emergency_stop):
    """Everything `Server2.wsgi` touches while handling a crash."""
    from types import SimpleNamespace

    done = []
    fake = SimpleNamespace(
        colloquy=SimpleNamespace(emergency_stop=emergency_stop),
        shutdown_event=SimpleNamespace(set=lambda: done.append("server asked to stop")),
        log=lambda message: done.append("logged"),
    )
    fake.done = done
    return fake


def _crashing_wsgi(monkeypatch):
    from colloquy import server2

    def boom(**kwargs):
        raise _Boom("the original crash")

    monkeypatch.setattr(server2, "WSGI2", boom)


def test_a_crash_becomes_an_emergency_stop(monkeypatch):
    """An unhandled exception only kills the HTTP loop; it does not touch
    `BaseThread._shutdown`. So any hardware thread still running would go
    on moving unsupervised with no UI left to stop it."""
    from colloquy.server2 import Server2

    _crashing_wsgi(monkeypatch)
    stopped = []
    fake = _server_double(lambda: stopped.append("emergency stop"))

    with pytest.raises(_Boom):
        Server2.wsgi(fake, {}, None)

    assert stopped == ["emergency stop"]
    assert "server asked to stop" in fake.done


def test_an_emergency_stop_that_fails_does_not_take_the_handler_with_it(monkeypatch):
    """The traceback this was written after.

    The emergency stop itself raised - a bare AssertionError out of
    `U2D2.open`, on an installation whose main PCB was noted as unmounted
    - and took the rest of the handler with it. The server was never
    asked to stop, and what reached wsgiref was the *second* exception,
    with the first nowhere in it. A handler that can fail the same way as
    the thing it is handling is not a handler.
    """
    from colloquy.server2 import Server2

    _crashing_wsgi(monkeypatch)

    def explode():
        raise RuntimeError("the servo bus is not there")

    fake = _server_double(explode)

    with pytest.raises(_Boom):
        Server2.wsgi(fake, {}, None)

    # The original survives, the secondary is written down, and the
    # server is still told to stop.
    assert "server asked to stop" in fake.done
    assert "logged" in fake.done
