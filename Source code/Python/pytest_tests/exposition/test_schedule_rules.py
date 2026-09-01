"""Reading and writing a schedule.

The whole of what this file is worried about is a schedule that is
*almost* right. A schedule nobody can parse announces itself; a schedule
that parses and means something slightly different than it looks is a
dark room on a day somebody thought they had opened, and nothing says so
until the day arrives. So the refusals are pinned as hard as the
successes, and so are the two round trips - text and params - because
those are the two ways a schedule survives being looked at.
"""
import pytest

from colloquy.exposition.schedule.rules import (
    CLOSED,
    WEEKDAYS,
    Rules,
    ScheduleError,
    Window,
    format_rules,
    from_params,
    parse,
    to_params,
)

A_WEEK = """
# a run at the ZKM
from 2026-09-15
to   2026-09-30

monday     closed
tuesday    10:00-13:00, 14:00-18:00
wednesday  10:00-18:00
thursday   10:00-20:00
friday     10:00-18:00
saturday   11:00-19:00
sunday     11:00-19:00

open   2026-09-21  14:00-18:00
closed 2026-09-24
"""


# --- the shape of a schedule ---------------------------------------------


def test_an_empty_schedule_is_the_default_and_says_so():
    """No schedule is a real state, not a broken one: it is what a fresh
    params.json has, and it means the piece is started by hand."""
    rules = parse("")

    assert rules.is_empty
    assert not rules.has_a_run
    assert rules.starts_on is None


def test_a_comment_only_schedule_is_still_empty():
    assert parse("# nothing decided yet\n\n   \n").is_empty


def test_the_run_is_read():
    rules = parse(A_WEEK)

    assert str(rules.starts_on) == "2026-09-15"
    assert str(rules.ends_on) == "2026-09-30"
    assert rules.has_a_run


def test_a_start_with_no_end_is_not_a_run():
    """Nothing in it ever says stop, which is the one thing a schedule
    has to be able to say before the piece is left with it."""
    rules = parse("from 2026-09-15")

    assert not rules.is_empty
    assert not rules.has_a_run


def test_every_weekday_is_present_even_when_unwritten():
    """Two schedules describing the same week are the same schedule.

    A file naming three weekdays and one naming all seven and closing
    four of them say exactly the same thing, and if they compared unequal
    every round-trip check here would silently become a test of which
    lines somebody happened to type.
    """
    rules = parse("tuesday 10:00-18:00")

    assert set(rules.weekly) == set(WEEKDAYS)
    assert rules.weekly["monday"] == ()
    assert rules == parse(
        "\n".join(
            ["tuesday 10:00-18:00"]
            + [f"{day} {CLOSED}" for day in WEEKDAYS if day != "tuesday"]
        )
    )


def test_hours_are_read_as_minutes_since_midnight():
    rules = parse("wednesday 10:00-18:30")

    assert rules.weekly["wednesday"] == (Window(600, 1110),)
    assert rules.weekly["wednesday"][0].label == "10:00-18:30"
    assert rules.weekly["wednesday"][0].minutes == 510


def test_a_day_can_have_two_stretches_and_they_come_out_sorted():
    """A gallery with a lunchtime closing. Written as one stretch it
    would leave the piece moving in an empty room for an hour a day."""
    rules = parse("tuesday 14:00-18:00, 10:00-13:00")

    assert [w.label for w in rules.weekly["tuesday"]] == [
        "10:00-13:00",
        "14:00-18:00",
    ]


def test_commas_are_optional():
    assert parse("tuesday 10:00-13:00 14:00-18:00") == parse(
        "tuesday 10:00-13:00, 14:00-18:00"
    )


def test_a_closing_day_has_to_be_said_out_loud():
    """An empty line is also what a half-typed schedule looks like."""
    assert parse("monday closed").weekly["monday"] == ()

    with pytest.raises(ScheduleError) as raised:
        parse("monday")
    assert "closed" in str(raised.value)


# --- the two kinds of exception ------------------------------------------


def test_an_exceptional_running_date_carries_its_own_hours():
    rules = parse(A_WEEK)

    from datetime import date

    assert [w.label for w in rules.exceptionally_running[date(2026, 9, 21)]] == [
        "14:00-18:00"
    ]


def test_an_exceptional_running_date_without_hours_is_refused():
    """It cannot fall back on its weekday - the whole reason it is
    written is that its weekday says the wrong thing."""
    with pytest.raises(ScheduleError) as raised:
        parse("open 2026-09-21")
    assert "hours" in str(raised.value)


def test_an_exceptional_standby_date_is_just_a_date():
    from datetime import date

    assert parse(A_WEEK).exceptionally_standby == (date(2026, 9, 24),)


# --- what is refused, and where ------------------------------------------


def test_the_line_number_is_named():
    with pytest.raises(ScheduleError) as raised:
        parse("from 2026-09-15\nto 2026-09-30\nnonsense here\n")

    assert raised.value.line_number == 3
    assert "line 3" in str(raised.value)
    assert "nonsense" in str(raised.value)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("from yesterday", "not a date"),
        ("tuesday 10:00", "stretch of hours"),
        ("tuesday 25:00-26:00", "not a time on the clock"),
        ("tuesday 10:70-11:00", "not a time on the clock"),
        ("tuesday ten-eleven", "not a time"),
        ("tuesday 18:00-10:00", "ends before it starts"),
        ("tuesday 18:00-18:00", "ends before it starts"),
        ("tuesday 10:00-13:00 12:00-18:00", "overlap"),
        ("tuesday 10:00-18:00\ntuesday 11:00-12:00", "given twice"),
        ("from 2026-01-01\nfrom 2026-02-01", "already has a start date"),
        ("to 2026-01-01\nto 2026-02-01", "already has an end date"),
        ("from 2026-09-30\nto 2026-09-15", "ends (2026-09-15) before it starts"),
        ("closed 2026-09-24\nclosed 2026-09-24", "already a standby day"),
        ("open 2026-09-21 10:00-11:00\nopen 2026-09-21 12:00-13:00", "already an open"),
        ("from 2026-09-15 2026-09-16", "takes one date"),
    ],
)
def test_what_a_schedule_will_not_accept(text, expected):
    with pytest.raises(ScheduleError) as raised:
        parse(text)
    assert expected in str(raised.value)


def test_a_date_written_both_ways_is_refused_rather_than_arbitrated():
    """Two sentences that contradict each other. Refusing here is what
    lets the solver have no opinion about which one wins."""
    with pytest.raises(ScheduleError) as raised:
        parse("open 2026-09-21 10:00-11:00\nclosed 2026-09-21")

    assert "both an open day and a standby day" in str(raised.value)


def test_a_stretch_over_midnight_says_how_to_write_it():
    with pytest.raises(ScheduleError) as raised:
        parse("saturday 22:00-02:00")

    assert "midnight" in str(raised.value)


# --- round trips ----------------------------------------------------------


def test_the_text_form_round_trips():
    rules = parse(A_WEEK)

    assert parse(format_rules(rules)) == rules


def test_the_params_form_round_trips():
    rules = parse(A_WEEK)

    assert from_params(to_params(rules)) == rules


def test_an_empty_schedule_round_trips_through_both():
    assert parse(format_rules(Rules())).is_empty
    assert from_params(to_params(Rules())).is_empty


def test_saving_hours_cannot_switch_the_schedule_on():
    """`enabled` is the switch, not the schedule. If it travelled with
    the hours, editing opening times would be a way to hand the piece to
    the clock without ever pressing the thing that says so."""
    assert "enabled" not in to_params(parse(A_WEEK))


def test_an_unwritten_run_persists_as_empty_strings_not_none():
    stored = to_params(Rules())

    assert stored["starts on"] == ""
    assert stored["ends on"] == ""
    assert stored["weekly"] == {day: [] for day in WEEKDAYS}


# --- params.json is hand-editable too -------------------------------------


@pytest.mark.parametrize(
    "section, expected",
    [
        ({"starts on": "the 15th"}, "not a date"),
        ({"weekly": {"someday": []}}, "not a weekday"),
        ({"weekly": {"monday": ["10:00"]}}, "stretch of hours"),
        ({"exceptional standby": ["nope"]}, "not a date"),
        ({"exceptional running": {"2026-09-21": ["nope"]}}, "stretch of hours"),
        ({"starts on": "2026-09-30", "ends on": "2026-09-15"}, "before it starts"),
        ({"starts on": 20260915}, "written as YYYY-MM-DD"),
    ],
)
def test_junk_in_params_fails_as_a_sentence(section, expected):
    """Strings and lists are read-only on the params page, so the way a
    bad value gets in is somebody with a text editor. It has to arrive as
    a sentence on the schedule's own page, not as a ValueError out of a
    request."""
    with pytest.raises(ScheduleError) as raised:
        from_params(section)

    assert expected in str(raised.value)
    assert raised.value.line_number is None


def test_an_empty_list_in_params_is_a_closing_day():
    """The two forms differ here on purpose: in the text a bare weekday
    is a half-typed line, in params an empty list is what every weekday
    starts as."""
    assert from_params({"weekly": {"monday": []}}).weekly["monday"] == ()
