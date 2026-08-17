"""Unit tests for Female.loop() - the small state machine that decides,
once per tick, whether she should be looking for a male or answering one.

Called unbound against doubles, per conftest.py: a real Female reaches
into u2d2/arduino at construction.
"""
from types import SimpleNamespace

from colloquy.hardware.female import Female


def make_female(satisfied=False, partner=None, searching=False,
                reinforcing=False, reinforcement_errors=False):
    started = []

    search = SimpleNamespace(
        is_started=searching,
        take_partner=lambda: partner,
        start=lambda started_by=None: started.append("search"),
    )
    reinforcement = SimpleNamespace(
        is_started=reinforcing,
        thread_errors=reinforcement_errors,
        partner=None,
        start=lambda started_by=None: started.append("reinforcement"),
    )
    fake = SimpleNamespace(
        search=search,
        reinforcement=reinforcement,
        is_satisfied=lambda: satisfied,
    )
    fake.started = started
    return fake


def test_an_unsatisfied_female_starts_looking():
    fake = make_female(satisfied=False)

    Female.loop(fake)

    assert fake.started == ["search"]


def test_a_satisfied_female_does_nothing():
    fake = make_female(satisfied=True)

    Female.loop(fake)

    assert fake.started == []


def test_nothing_is_started_while_she_is_already_looking():
    fake = make_female(satisfied=False, searching=True)

    Female.loop(fake)

    assert fake.started == []


def test_nothing_is_started_while_she_is_reinforcing():
    fake = make_female(satisfied=False, reinforcing=True)

    Female.loop(fake)

    assert fake.started == []


def test_a_finished_search_that_found_someone_starts_reinforcement():
    # The point of the whole thread: a match now has a consequence.
    fake = make_female(satisfied=False, partner=("male1", "O"))

    Female.loop(fake)

    assert fake.started == ["reinforcement"]
    assert fake.reinforcement.partner == ("male1", "O")


def test_she_does_not_go_back_to_searching_before_reinforcing():
    # She is still unsatisfied - without the find being handled first she
    # would just start looking again and the find would be lost.
    fake = make_female(satisfied=False, partner=("male2", "P"))

    Female.loop(fake)

    assert "search" not in fake.started


def test_a_failed_reinforcement_stops_her_rather_than_spinning():
    # Reinforcement is a placeholder that errors on its first tick, and
    # BaseThread refuses to restart an errored thread - retrying would
    # raise inside her own loop every tick and bury the original error.
    fake = make_female(satisfied=False, partner=("male1", "O"),
                       reinforcement_errors=True)

    Female.loop(fake)

    assert fake.started == []
