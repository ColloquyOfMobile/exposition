"""Starting the piece with no Arduino link refuses instead of crashing.

2026-11-24, on the bench: the Arduino port was COM6 with no board on it.
`start` ran every body, each failed on its first command, and the error
path latched the class-level shutdown - nothing could start again until a
restart. Unbound calls against doubles, per conftest: nothing started.
"""
from types import SimpleNamespace

from colloquy.exposition import Exposition


def fake(is_open):
    started = []
    logged = []
    arduino = SimpleNamespace(is_open=is_open, port_name="COM6")
    drivers = SimpleNamespace(arduino=arduino, start=lambda started_by: started.append(started_by))
    node = SimpleNamespace(drivers=drivers, log=logged.append, _refusal=None)
    node.why_not_start = lambda: Exposition.why_not_start(node)
    return node, started, logged


def test_no_link_refuses_and_starts_nothing():
    node, started, logged = fake(is_open=False)

    Exposition.setup(node)

    assert started == []
    assert "'COM6'" in node._refusal and "simulated arduino port" in node._refusal
    assert logged and logged[0].startswith("Not started")


def test_an_open_link_starts_the_drivers():
    node, started, _ = fake(is_open=True)

    Exposition.setup(node)

    assert started == [node]
    assert node._refusal is None


def test_a_link_that_cannot_be_asked_is_a_refusal_not_a_crash():
    class Broken:
        @property
        def is_open(self):
            raise OSError("handle gone")

    node = SimpleNamespace(drivers=SimpleNamespace(arduino=Broken()))

    assert "cannot be asked" in Exposition.why_not_start(node)


# --- an error stops the piece, not the process ---------------------------

from pathlib import Path  # noqa: E402

from colloquy.base_thread import BaseThread  # noqa: E402


class Worker(BaseThread):
    scenario_names = ()

    def __init__(self, owner, name):
        self._name = name
        super().__init__(owner=owner)

    @property
    def name(self):
        return self._name


def piece():
    """A fake exposition over a real (never started) tree: drivers with a
    body, the body with a worker - the shape failed_threads walks."""
    root = SimpleNamespace(owners=[], name="", path=Path(), is_simulated=True)
    drivers = Worker(owner=root, name="drivers")
    body = Worker(owner=drivers, name="female1")
    drives = Worker(owner=body, name="drives")
    drivers["female1"] = body
    body["drives"] = drives
    stopped = []
    drivers.stop = lambda: stopped.append(True)
    node = SimpleNamespace(
        drivers=drivers, _dict={}, _error_stop=None, _refusal=None,
        log=lambda text: None, is_started=False,
    )
    node.failed_threads = lambda: Exposition.failed_threads(node)
    node.has_errors = lambda: Exposition.has_errors(node)
    return node, drives, stopped


def test_an_error_deep_in_the_tree_is_found_and_said():
    node, drives, stopped = piece()
    drives.thread_errors.append(RuntimeError("could not open port 'COM6'"))

    Exposition.setdown(node)

    assert node.failed_threads() == [drives]
    assert "drivers/female1/drives" in node._error_stop
    assert stopped == [True]


def test_stopping_on_an_error_no_longer_latches_the_process():
    node, drives, _ = piece()
    drives.thread_errors.append(RuntimeError("boom"))
    BaseThread._shutdown.clear()

    Exposition.setdown(node)

    assert not BaseThread._shutdown.is_set()


def test_a_start_after_an_error_waits_for_the_person():
    node, drives, _ = piece()
    drives.thread_errors.append(RuntimeError("boom"))

    Exposition.start(node)

    assert "clear the errors and start again" in node._refusal


def test_clearing_forgets_the_errors_and_starts_again():
    node, drives, _ = piece()
    drives.thread_errors.append(RuntimeError("boom"))
    node._error_stop = "earlier"
    starts = []
    node.start = lambda started_by=None: starts.append(started_by)

    Exposition.clear_errors_and_start(node)

    assert node.failed_threads() == []
    assert not drives.thread_errors
    assert node._error_stop is None
    assert starts == [None]
