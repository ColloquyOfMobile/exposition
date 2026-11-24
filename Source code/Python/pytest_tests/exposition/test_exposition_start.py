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
