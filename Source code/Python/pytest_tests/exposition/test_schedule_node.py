"""The node: the switch, the editor, and the one call that moves servos.

`rules` and `solver` decide what a schedule *says*. This file is about
what the piece then *does*, which is where the consequences are - an
enabled schedule is the only thing in this repository that starts the
installation with nobody in the room.

Three behaviours are worth more than the rest, and each is here because
getting it wrong is quiet rather than loud:

- it stops only what it started, so a technician kneeling at the rack at
  nine in the evening is not overruled by a clock;
- it refuses to start the piece against the hardware notes, because
  unplugging the motors deliberately does *not* latch the shutdown event
  and an enabled schedule would otherwise call start every twenty
  seconds at a bus that was never opened;
- saving hours cannot switch it on, and switching it on with no run of
  dates is refused.

A real `ExpositionSchedule` is built here, with a stub owner - see the
conftest note about `owners=[]`. Nothing is ever `.start()`ed: the two
places the class would do that are replaced on the instance, and what is
checked is that they were called.
"""
from datetime import datetime
from types import SimpleNamespace

import pytest

from colloquy.exposition.schedule import ExpositionSchedule
from colloquy.exposition.schedule.rules import ENABLED
from colloquy.params import DEFAULTS

A_WEEK = """
from 2026-09-15
to   2026-09-30
tuesday    10:00-18:00
wednesday  10:00-18:00
closed 2026-09-16
"""

OPEN_HOURS = datetime(2026, 9, 15, 12, 0)
SHUT_HOURS = datetime(2026, 9, 15, 22, 0)


@pytest.fixture
def schedule(stub_factory):
    """A real node with nothing behind it.

    `params` is a plain dict rather than a `Params`, so the test never
    touches local/params.json - what is checked is the writing, not the
    persisting, which params.py has its own tests for.
    """
    exposition_calls: list = []

    def fake_start(**kwargs):
        # As the real one: Thread.start() returns with the thread alive,
        # so is_started is True by the time start() has returned. The
        # schedule reads it back to decide whether it is now holding the
        # piece, so a double that did not flip it would let
        # "stops only what it started" pass by never starting anything.
        exposition_calls.append(("start", kwargs))
        exposition.is_started = True

    def fake_stop():
        exposition_calls.append(("stop", {}))
        exposition.is_started = False

    exposition = stub_factory(
        owners=[],
        is_started=False,
        thread_errors=[],
        start=fake_start,
        stop=fake_stop,
    )
    exposition.calls = exposition_calls

    hardware = SimpleNamespace(
        main_pcb=SimpleNamespace(is_mounted=True),
        motors=SimpleNamespace(is_plugged_in=True),
    )
    # A fresh copy of the shipped defaults, which is what a new
    # installation actually gets.
    params = {"exposition schedule": dict(DEFAULTS["exposition schedule"])}
    params["exposition schedule"]["weekly"] = dict(
        DEFAULTS["exposition schedule"]["weekly"]
    )
    exposition.colloquy = SimpleNamespace(params=params, hardware=hardware)

    node = ExpositionSchedule(owner=exposition)
    # The watch is a thread and this suite never starts one; what matters
    # is that `enable` asks for it.
    node.watch_calls = []
    node.start = lambda **kwargs: node.watch_calls.append(kwargs)
    return node


# --- the default is no schedule at all -----------------------------------


def test_a_fresh_installation_has_no_schedule(schedule):
    """Which is the whole of the default behaviour: somebody opens the
    page and presses start, exactly as before any of this existed."""
    assert schedule.is_enabled is False
    assert schedule.rules.is_empty
    assert schedule.read_rules()[1] is None


def test_with_no_schedule_nothing_is_acted_on(schedule):
    assert "disabled" in schedule.apply_now(OPEN_HOURS)
    assert schedule.exposition.calls == []


# --- writing one ----------------------------------------------------------


def test_saving_writes_the_structure_into_params(schedule):
    schedule.save(A_WEEK)

    section = schedule.section
    assert section["starts on"] == "2026-09-15"
    assert section["ends on"] == "2026-09-30"
    assert section["weekly"]["tuesday"] == ["10:00-18:00"]
    assert section["weekly"]["monday"] == []
    assert section["exceptional standby"] == ["2026-09-16"]


def test_saving_does_not_switch_it_on(schedule):
    """The one thing that must never be a side effect of editing hours."""
    schedule.save(A_WEEK)

    assert schedule.is_enabled is False
    assert schedule.section[ENABLED] is False


def test_a_schedule_that_will_not_parse_is_kept_in_the_box(schedule):
    """Whoever typed it is one line from having it right. Handing them
    back the canonical form of the old schedule would lose the lot."""
    schedule.save(A_WEEK)
    broken = A_WEEK + "\nfriday 18:00-10:00\n"

    schedule.save(broken)

    assert schedule._draft == broken
    assert "ends before it starts" in schedule._draft_error
    # And the schedule that was already saved is untouched.
    assert schedule.section["starts on"] == "2026-09-15"


def test_the_editor_opens_on_the_saved_schedule(schedule):
    schedule.save(A_WEEK)
    schedule.enter_edit()

    assert "from 2026-09-15" in schedule._draft
    assert "closed  2026-09-16" in schedule._draft


def test_cancelling_throws_the_draft_away(schedule):
    schedule.enter_edit()
    schedule._draft = "nonsense"
    schedule.cancel()

    assert schedule._draft is None
    assert schedule._mode == "view"


# --- the switch -----------------------------------------------------------


def test_enabling_with_no_run_of_dates_is_refused(schedule):
    """An enabled schedule with no dates reads as an installation under
    control and behaves as one that is not."""
    outcome = schedule.enable()

    assert "refused" in outcome
    assert schedule.is_enabled is False
    assert schedule.watch_calls == []


def test_enabling_with_a_run_writes_the_note_and_starts_the_watch(schedule):
    schedule.save(A_WEEK)

    schedule.enable()

    assert schedule.is_enabled is True
    assert schedule.section[ENABLED] is True
    assert schedule.watch_calls == [{"started_by": None}]


def test_disabling_writes_the_note_and_leaves_a_running_show_alone(schedule):
    """Disabling says "stop deciding for me". A show being watched by
    visitors is not something to end as a side effect of that."""
    schedule.save(A_WEEK)
    schedule.enable()
    schedule.exposition.is_started = True

    schedule.disable()

    assert schedule.is_enabled is False
    assert ("stop", {}) not in schedule.exposition.calls


def test_the_note_is_what_survives_a_restart(schedule):
    schedule.save(A_WEEK)
    schedule.enable()

    assert schedule.start_if_enabled() is True

    schedule.disable()
    schedule.watch_calls.clear()

    assert schedule.start_if_enabled() is False
    assert schedule.watch_calls == []


# --- acting on the clock --------------------------------------------------


def enabled(schedule):
    schedule.save(A_WEEK)
    schedule.enable()
    return schedule


def test_it_starts_the_piece_within_opening_hours(schedule):
    enabled(schedule)

    outcome = schedule.apply_now(OPEN_HOURS)

    assert "started the exposition" in outcome
    assert schedule.exposition.calls == [("start", {"started_by": None})]


def test_it_does_nothing_when_the_piece_is_already_as_asked(schedule):
    enabled(schedule)
    schedule.exposition.is_started = True

    assert schedule.apply_now(OPEN_HOURS) is None
    assert schedule.exposition.calls == []


def test_it_stops_the_piece_it_started_at_closing_time(schedule):
    enabled(schedule)
    schedule.apply_now(OPEN_HOURS)
    assert schedule.exposition.is_started
    schedule.exposition.calls.clear()

    outcome = schedule.apply_now(SHUT_HOURS)

    assert "stopped the exposition" in outcome
    assert schedule.exposition.calls == [("stop", {})]


def test_it_leaves_a_show_started_by_hand_alone(schedule):
    """A technician at the rack at nine in the evening is making a
    decision, and a clock is not the thing that should overrule it."""
    enabled(schedule)
    schedule.exposition.is_started = True

    outcome = schedule.apply_now(SHUT_HOURS)

    assert "started by hand" in outcome
    assert schedule.exposition.calls == []


def test_a_standby_date_keeps_the_piece_off(schedule):
    enabled(schedule)

    assert schedule.apply_now(datetime(2026, 9, 16, 12, 0)) is None
    assert schedule.exposition.calls == []


def test_outside_the_run_the_piece_is_never_started(schedule):
    enabled(schedule)

    assert schedule.apply_now(datetime(2026, 10, 5, 12, 0)) is None
    assert schedule.exposition.calls == []


# --- refusing to act against the hardware notes ---------------------------


def test_it_will_not_start_the_piece_with_the_motors_unplugged(schedule):
    """`hardware/motors` deliberately does not latch the shutdown event -
    the whole point is that the bench goes on being useful - so nothing
    else would stop this calling start at a bus that was never opened,
    every twenty seconds, for as long as the chain was out."""
    enabled(schedule)
    schedule.colloquy.hardware.motors.is_plugged_in = False

    outcome = schedule.apply_now(OPEN_HOURS)

    assert "motors are noted as unplugged" in outcome
    assert schedule.exposition.calls == []


def test_it_will_not_start_the_piece_with_the_main_pcb_out(schedule):
    enabled(schedule)
    schedule.colloquy.hardware.main_pcb.is_mounted = False

    outcome = schedule.apply_now(OPEN_HOURS)

    assert "main PCB is noted as unmounted" in outcome
    assert schedule.exposition.calls == []


def test_it_will_not_restart_an_exposition_that_stopped_on_an_error(schedule):
    """`BaseThread.start` raises on a thread carrying errors, so trying
    would turn a stopped show into a failing schedule."""
    enabled(schedule)
    schedule.exposition.thread_errors = ["something went wrong"]

    outcome = schedule.apply_now(OPEN_HOURS)

    assert "stopped on an error" in outcome
    assert schedule.exposition.calls == []


def test_a_hardware_note_never_blocks_a_stop(schedule):
    """Refusing to start is care; refusing to stop would leave the piece
    running past closing because of a note about a cable."""
    enabled(schedule)
    schedule.apply_now(OPEN_HOURS)
    schedule.exposition.calls.clear()
    schedule.colloquy.hardware.motors.is_plugged_in = False

    outcome = schedule.apply_now(SHUT_HOURS)

    assert "stopped the exposition" in outcome


# --- an unreadable schedule -----------------------------------------------


def test_junk_in_params_is_reported_and_nothing_is_acted_on(schedule):
    schedule.section["starts on"] = "the fifteenth"
    schedule.section[ENABLED] = True

    rules, unreadable = schedule.read_rules()

    assert rules.is_empty
    assert "not a date" in unreadable
    assert "cannot be read" in schedule.apply_now(OPEN_HOURS)
    assert schedule.exposition.calls == []


def test_enabling_an_unreadable_schedule_is_refused(schedule):
    schedule.section["starts on"] = "the fifteenth"

    outcome = schedule.enable()

    assert "refused" in outcome
    assert schedule.is_enabled is False


# --- the page -------------------------------------------------------------


def test_the_page_offers_one_switch_and_not_the_bare_thread_links(schedule):
    """`start`/`stop` would be a second, unlabelled way to say the same
    thing as `enable` - and a way to have the clock starting the piece
    while the page read "disabled"."""
    states = schedule._snapshot_if_opened(("app", "exposition", "schedule"))

    assert "start" not in states
    assert "stop" not in states
    assert "enable" in states
    assert "disable" in states


def test_the_page_says_which_hand_started_the_piece(schedule):
    enabled(schedule)
    schedule.exposition.is_started = True

    states = schedule._snapshot_if_opened(("app", "exposition", "schedule"))

    assert states["started by"]["value"] == "hand"


def test_the_full_schedule_hangs_off_it(schedule):
    assert "full schedule" in schedule.snapshot_children


def test_the_full_schedule_draws_the_run(schedule):
    enabled(schedule)
    full = schedule.snapshot_children["full schedule"]

    states = full._snapshot_if_opened(("app", "exposition", "schedule", "full"))

    assert states["days in the run"]["value"] == 16
    assert "2026-09-16" in states["solved"]["html"]
    assert "exceptionally standby" in states["solved"]["html"]


def test_the_full_schedule_says_when_there_is_nothing_to_work_out(schedule):
    full = schedule.snapshot_children["full schedule"]

    states = full._snapshot_if_opened(("app", "exposition", "schedule", "full"))

    assert "started by hand" in states["solved"]["html"]
