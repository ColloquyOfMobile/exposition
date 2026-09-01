# -*- coding: utf-8 -*-
# Source code/Python/colloquy/exposition/schedule/solver.py

"""The rules worked out into days: every date of the run and its hours.

A schedule is written as a general statement plus its exceptions, which
is the only way anybody would want to write one and the worst possible
way to check one. Nobody can read

    tuesday 10:00-18:00
    closed 2026-11-01

and be sure what happens on the first of November without doing the
arithmetic in their head, and the arithmetic in their head is exactly
what a schedule is meant to replace. So the rules are expanded: one row
per date between the two ends of the run, with its hours and *why* they
are its hours - the week, or the line that broke it.

**This is the same move `scenario_browser/rendering.py` makes**, and for
the same reason. A scenario is written with `->` includes and read as one
flat clock; a schedule is written as a week with exceptions and read as a
list of days. In both cases the thing somebody has to check is not the
thing anybody would write.

**One clock, and it is this machine's.** Everything here is naive local
time. The installation's laptop stands in the room the piece is in, its
clock is the clock on the wall, and a gallery's opening hours are local
by definition. The one place it shows is a daylight-saving change, where
an hour is repeated or missing: the piece then opens an hour early or
late on that one morning, which is a thing to know rather than a thing
worth carrying a timezone database for.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import NamedTuple

from .rules import WEEKDAYS, Rules, Window

# Why a day has the hours it has. Prose rather than an enum because it is
# read off the page by a person, and there are exactly three of them.
FROM_THE_WEEK = "the week"
EXCEPTIONALLY_RUNNING = "exceptionally running"
EXCEPTIONALLY_STANDBY = "exceptionally standby"

# How many days the expansion will draw. A run of a few months is a few
# hundred rows, which is a page; a typo in a year ("to 2126-12-20") is
# thirty-six thousand, which is a page nobody can load and a request that
# holds the one command lock while it renders. The node says when it has
# truncated, so the typo is visible rather than merely survivable.
MAX_DAYS = 800

# How far ahead `next_change` will look before giving up. A run whose
# every remaining day is closed has no next change, and saying so beats
# walking to the end of it on every page load.
SCAN_DAYS = 400


class Day(NamedTuple):
    """One date of the run, resolved."""

    on: date
    weekday: str
    windows: tuple[Window, ...]
    reason: str

    @property
    def is_running(self) -> bool:
        return bool(self.windows)

    @property
    def hours(self) -> str:
        return "  ".join(window.label for window in self.windows)

    @property
    def minutes(self) -> int:
        return sum(window.minutes for window in self.windows)


class Totals(NamedTuple):
    days: int
    running_days: int
    standby_days: int
    minutes: int

    @property
    def hours(self) -> float:
        return self.minutes / 60.0


def weekday_of(when: date) -> str:
    return WEEKDAYS[when.weekday()]


def resolve(rules: Rules, when: date) -> Day:
    """One date's hours, and which rule gave them.

    Precedence is standby, then running, then the week. It never actually
    arbitrates between the first two - `rules.parse` and `from_params`
    both refuse a date written as both - but the order is stated because
    a reader will ask, and the answer should not be "it depends which
    dict was checked first".
    """
    weekday = weekday_of(when)

    if when in rules.exceptionally_standby:
        return Day(when, weekday, (), EXCEPTIONALLY_STANDBY)

    windows = rules.exceptionally_running.get(when)
    if windows is not None:
        return Day(when, weekday, windows, EXCEPTIONALLY_RUNNING)

    return Day(when, weekday, rules.weekly.get(weekday, ()), FROM_THE_WEEK)


def is_within_the_run(rules: Rules, when: date) -> bool:
    """Outside the two dates nothing runs, and no exception changes that.

    An `open` line for a date after the end of the exhibition is not a
    day the piece runs - it is a line that does nothing, which is what
    `exceptions_outside_the_run` is for.
    """
    if not rules.has_a_run:
        return False
    assert rules.starts_on is not None and rules.ends_on is not None
    return rules.starts_on <= when <= rules.ends_on


def day_count(rules: Rules) -> int:
    """How many days the run is, whether or not they all get drawn."""
    if not rules.has_a_run:
        return 0
    assert rules.starts_on is not None and rules.ends_on is not None
    return (rules.ends_on - rules.starts_on).days + 1


def solve(rules: Rules, limit: int = MAX_DAYS) -> tuple[Day, ...]:
    """Every date of the run, in order, with its hours.

    Empty when there is no run to expand, which is the default state and
    not a fault: it means the piece is started by hand.
    """
    if not rules.has_a_run:
        return ()
    assert rules.starts_on is not None

    days = []
    for offset in range(min(day_count(rules), limit)):
        days.append(resolve(rules, rules.starts_on + timedelta(days=offset)))
    return tuple(days)


def totals(days: tuple[Day, ...]) -> Totals:
    running = [day for day in days if day.is_running]
    return Totals(
        days=len(days),
        running_days=len(running),
        standby_days=len(days) - len(running),
        minutes=sum(day.minutes for day in running),
    )


def exceptions_outside_the_run(rules: Rules) -> tuple[date, ...]:
    """Exception dates the run never reaches, so they do nothing.

    Not an error - somebody may be writing the exceptions before pinning
    the dates - but silently ignoring a line somebody typed is how a
    schedule comes to be trusted for something it does not say. The node
    reports these; it does not refuse them.
    """
    if not rules.has_a_run:
        return tuple(
            sorted(set(rules.exceptionally_running) | set(rules.exceptionally_standby))
        )
    written = set(rules.exceptionally_running) | set(rules.exceptionally_standby)
    return tuple(sorted(when for when in written if not is_within_the_run(rules, when)))


# --- what the clock says right now ---------------------------------------


def minute_of_day(moment: datetime) -> int:
    return moment.hour * 60 + moment.minute


def is_running_at(rules: Rules, moment: datetime) -> bool:
    """Should the piece be live at this instant?

    The whole of what the scheduler asks. Everything else on the node is
    a way of showing a person what this function is going to say.
    """
    if not is_within_the_run(rules, moment.date()):
        return False
    minute = minute_of_day(moment)
    return any(
        window.contains(minute) for window in resolve(rules, moment.date()).windows
    )


def next_change(
    rules: Rules, moment: datetime, scan_days: int = SCAN_DAYS
) -> tuple[datetime, bool] | None:
    """When the answer above next flips, and to what. None if it does not.

    Every boundary is the edge of a window, so the candidates are the
    opening and closing times of each remaining day rather than every
    minute. The first one after `moment` whose state differs is the
    answer - windows are sorted and cannot overlap, so there is no
    subtler ordering to get wrong.
    """
    if not rules.has_a_run:
        return None
    assert rules.starts_on is not None and rules.ends_on is not None

    now_running = is_running_at(rules, moment)
    first = max(moment.date(), rules.starts_on)

    when = first
    for _ in range(scan_days):
        if when > rules.ends_on:
            break
        for window in resolve(rules, when).windows:
            for minute, running_after in ((window.opens, True), (window.closes, False)):
                at = datetime.combine(when, datetime.min.time()) + timedelta(
                    minutes=minute
                )
                if at > moment and running_after != now_running:
                    return at, running_after
        when += timedelta(days=1)

    return None
