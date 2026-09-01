"""Working a schedule out into days.

The solver is the part somebody stands in front of the rack and trusts,
so what is pinned here is the arithmetic they would otherwise be doing in
their head: which rule won on this date, whether the piece is live at
this minute, and when that next changes.

The half-open window is the one to look at twice. A stretch written
10:00-18:00 is shut *at* 18:00, not one minute after - the other
convention leaves the piece moving for a minute past every closing time,
which nobody reports and everybody notices.
"""
from datetime import date, datetime

import pytest

from colloquy.exposition.schedule.rules import Rules, Window, parse
from colloquy.exposition.schedule.solver import (
    EXCEPTIONALLY_RUNNING,
    EXCEPTIONALLY_STANDBY,
    FROM_THE_WEEK,
    day_count,
    exceptions_outside_the_run,
    is_running_at,
    next_change,
    resolve,
    solve,
    totals,
)

# 2026-09-15 is a Tuesday; 2026-09-30 a Wednesday.
A_WEEK = parse(
    """
from 2026-09-15
to   2026-09-30

monday     closed
tuesday    10:00-13:00, 14:00-18:00
wednesday  10:00-18:00
thursday   10:00-18:00
friday     10:00-18:00
saturday   11:00-19:00
sunday     11:00-19:00

open   2026-09-21  14:00-18:00
closed 2026-09-24
"""
)


# --- one date at a time ---------------------------------------------------


def test_an_ordinary_day_comes_from_the_week():
    day = resolve(A_WEEK, date(2026, 9, 16))

    assert day.weekday == "wednesday"
    assert day.hours == "10:00-18:00"
    assert day.reason == FROM_THE_WEEK
    assert day.is_running


def test_a_closing_weekday_is_dark_and_says_which_rule_did_it():
    day = resolve(A_WEEK, date(2026, 9, 28))  # a Monday

    assert not day.is_running
    assert day.reason == FROM_THE_WEEK


def test_an_exceptionally_running_date_beats_its_weekday():
    day = resolve(A_WEEK, date(2026, 9, 21))  # a Monday, normally closed

    assert day.hours == "14:00-18:00"
    assert day.reason == EXCEPTIONALLY_RUNNING


def test_an_exceptionally_standby_date_beats_its_weekday():
    day = resolve(A_WEEK, date(2026, 9, 24))  # a Thursday, normally open

    assert not day.is_running
    assert day.reason == EXCEPTIONALLY_STANDBY


def test_the_reason_is_the_point_of_the_column():
    """Two dark days, two completely different facts - and the one
    somebody is checking is nearly always the exception."""
    by_the_week = resolve(A_WEEK, date(2026, 9, 28))
    by_exception = resolve(A_WEEK, date(2026, 9, 24))

    assert by_the_week.is_running == by_exception.is_running
    assert by_the_week.reason != by_exception.reason


# --- the whole run --------------------------------------------------------


def test_the_run_is_expanded_end_to_end_inclusive():
    days = solve(A_WEEK)

    assert day_count(A_WEEK) == 16
    assert len(days) == 16
    assert days[0].on == date(2026, 9, 15)
    assert days[-1].on == date(2026, 9, 30)


def test_the_days_come_out_in_order():
    days = solve(A_WEEK)

    assert list(days) == sorted(days, key=lambda day: day.on)


def test_nothing_to_expand_without_both_ends_of_the_run():
    assert solve(parse("tuesday 10:00-18:00")) == ()
    assert solve(parse("from 2026-09-15\ntuesday 10:00-18:00")) == ()
    assert day_count(Rules()) == 0


def test_a_mistyped_year_is_truncated_rather_than_drawn():
    """Thirty-six thousand rows is a page nobody can load and a request
    holding the one command lock while it renders. The node says it has
    truncated, so the typo is visible rather than merely survivable."""
    huge = parse("from 2026-09-15\nto 2126-09-15\ntuesday 10:00-18:00")

    days = solve(huge, limit=50)

    assert len(days) == 50
    assert day_count(huge) > 36000


def test_the_totals_count_running_days_and_their_hours():
    counted = totals(solve(A_WEEK))

    assert counted.days == 16
    assert counted.running_days + counted.standby_days == counted.days
    # 2026-09-24 is a standby day; the two Mondays are closing days, but
    # one of them is an exceptional opening.
    assert counted.standby_days == 2
    assert counted.hours == pytest.approx(counted.minutes / 60.0)


def test_two_stretches_on_a_day_are_both_counted():
    one = totals(solve(parse("from 2026-09-15\nto 2026-09-15\ntuesday 10:00-18:00")))
    two = totals(
        solve(parse("from 2026-09-15\nto 2026-09-15\ntuesday 10:00-13:00 14:00-18:00"))
    )

    assert one.minutes == 8 * 60
    assert two.minutes == 7 * 60


# --- lines that do nothing ------------------------------------------------


def test_an_exception_outside_the_run_is_reported_not_refused():
    """Somebody may be writing the exceptions before pinning the dates.
    Silently ignoring a line they typed is how a schedule comes to be
    trusted for something it does not say."""
    rules = parse(
        "from 2026-09-15\nto 2026-09-30\nclosed 2027-01-01\nopen 2026-09-21 10:00-11:00"
    )

    assert exceptions_outside_the_run(rules) == (date(2027, 1, 1),)


def test_a_date_outside_the_run_never_runs_however_it_is_written():
    rules = parse("from 2026-09-15\nto 2026-09-30\nopen 2026-10-05 10:00-18:00")

    assert not is_running_at(rules, datetime(2026, 10, 5, 12, 0))


def test_without_a_run_every_exception_is_doing_nothing():
    rules = parse("closed 2027-01-01")

    assert exceptions_outside_the_run(rules) == (date(2027, 1, 1),)


# --- what the clock says --------------------------------------------------


def test_inside_a_window_the_piece_is_live():
    assert is_running_at(A_WEEK, datetime(2026, 9, 16, 11, 0))


def test_the_window_is_half_open_at_both_ends():
    assert is_running_at(A_WEEK, datetime(2026, 9, 16, 10, 0))
    assert is_running_at(A_WEEK, datetime(2026, 9, 16, 17, 59))
    assert not is_running_at(A_WEEK, datetime(2026, 9, 16, 18, 0))
    assert not is_running_at(A_WEEK, datetime(2026, 9, 16, 9, 59))


def test_the_gap_between_two_stretches_is_dark():
    assert is_running_at(A_WEEK, datetime(2026, 9, 15, 12, 0))
    assert not is_running_at(A_WEEK, datetime(2026, 9, 15, 13, 30))
    assert is_running_at(A_WEEK, datetime(2026, 9, 15, 15, 0))


def test_before_and_after_the_run_nothing_is_live():
    assert not is_running_at(A_WEEK, datetime(2026, 9, 14, 12, 0))
    assert not is_running_at(A_WEEK, datetime(2026, 10, 1, 12, 0))


def test_an_empty_schedule_is_never_live():
    assert not is_running_at(Rules(), datetime(2026, 9, 16, 11, 0))


# --- when it next changes -------------------------------------------------


def test_the_next_change_while_open_is_this_stretch_closing():
    assert next_change(A_WEEK, datetime(2026, 9, 16, 11, 0)) == (
        datetime(2026, 9, 16, 18, 0),
        False,
    )


def test_the_next_change_while_shut_is_the_next_opening():
    assert next_change(A_WEEK, datetime(2026, 9, 16, 8, 0)) == (
        datetime(2026, 9, 16, 10, 0),
        True,
    )


def test_the_next_change_before_the_run_is_the_first_opening():
    assert next_change(A_WEEK, datetime(2026, 9, 1, 8, 0)) == (
        datetime(2026, 9, 15, 10, 0),
        True,
    )


def test_the_next_change_skips_a_standby_day():
    """2026-09-24 is written closed, so the Wednesday evening's next
    change is the Friday morning."""
    assert next_change(A_WEEK, datetime(2026, 9, 23, 19, 0)) == (
        datetime(2026, 9, 25, 10, 0),
        True,
    )


def test_the_next_change_finds_an_exceptional_opening():
    assert next_change(A_WEEK, datetime(2026, 9, 20, 20, 0)) == (
        datetime(2026, 9, 21, 14, 0),
        True,
    )


def test_after_the_last_day_there_is_no_next_change():
    assert next_change(A_WEEK, datetime(2026, 9, 30, 19, 0)) is None


def test_a_schedule_with_no_run_never_changes():
    assert next_change(Rules(), datetime(2026, 9, 16, 11, 0)) is None


def test_a_run_of_only_closing_days_never_changes():
    rules = parse("from 2026-09-15\nto 2026-09-30")

    assert next_change(rules, datetime(2026, 9, 16, 11, 0)) is None


def test_the_scan_gives_up_rather_than_walking_a_mistyped_run():
    rules = parse("from 2026-09-15\nto 2126-09-15\nsunday 11:00-19:00")

    assert next_change(rules, datetime(2026, 9, 16, 11, 0), scan_days=2) is None
    assert next_change(rules, datetime(2026, 9, 16, 11, 0), scan_days=10) == (
        datetime(2026, 9, 20, 11, 0),
        True,
    )


def test_a_window_knows_what_it_contains():
    window = Window(600, 1080)

    assert window.contains(600)
    assert window.contains(1079)
    assert not window.contains(1080)
    assert not window.contains(599)
