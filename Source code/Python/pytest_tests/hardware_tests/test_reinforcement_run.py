# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware_tests/test_reinforcement_run.py

"""The reinforcement hardware test's own rules - the pure-logic parts.

The run itself needs bodies, a bar and a minute; what can be checked here
is what it refuses, and the shape of what it writes down. The second of
those is worth a test for the reason `test_search_events.py` gives: every
row is a line of CSV, and a comma in the wrong field silently moves every
column after it.
"""
from types import SimpleNamespace

# Renamed on import: pytest tries to collect anything called Test* and
# then warns that it cannot, because it takes a constructor.
from colloquy.tests.test_reinforcement import (
    TestReinforcement as ReinforcementTest,
)


class FakeDrive:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    @property
    def is_satisfied(self):
        return self.value < 12.5


def fake_body(name, o=100, p=100):
    return SimpleNamespace(
        name=name,
        drives=SimpleNamespace(
            o_drive=FakeDrive(f"{name}'s O drive", o),
            p_drive=FakeDrive(f"{name}'s P drive", p),
        ),
    )


def staged_node(male=None, female=None, drive="O"):
    node = ReinforcementTest.__new__(ReinforcementTest)
    node._male_name = "male1"
    node._female_name = "female1"
    node._drive_name = drive
    node._males = {"male1": male or fake_body("male1")}
    node._females = {"female1": female or fake_body("female1")}
    return node


# --- what it will not run against ----------------------------------------


def test_a_hungry_pair_can_run():
    assert staged_node()._why_not_run() is None


def test_it_refuses_a_pair_that_is_already_satisfied():
    """There would be nothing to take down, and the exchange would end on
    its first round looking like a success."""
    node = staged_node(male=fake_body("male1", o=0))

    refusal = node._why_not_run()

    assert refusal is not None
    assert "already satisfied" in refusal
    assert "make them both hungry" in refusal


def test_it_looks_at_the_drive_actually_being_shared():
    """A pair full of O and empty of P can run on O and not on P."""
    pair = dict(male=fake_body("male1", o=100, p=0),
                female=fake_body("female1", o=100, p=0))

    assert staged_node(drive="O", **pair)._why_not_run() is None
    assert staged_node(drive="P", **pair)._why_not_run() is not None


# --- and the row it writes ------------------------------------------------


def test_the_singing_column_never_contains_a_comma():
    """Both of them singing at once is an ordinary moment here - they
    alternate, and the bursts overlap at the edges. Joined with a comma it
    would move every band column one to the right for those rows only,
    which is the worst kind of wrong.
    """
    import inspect

    source = inspect.getsource(ReinforcementTest._record)

    assert '" + ".join(' in source
    assert '", ".join(' not in source.split("singing = ")[1].split("\n")[0]
