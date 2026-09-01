# -*- coding: utf-8 -*-
# Source code/Python/colloquy/exposition/schedule/rules.py

"""What the exposition schedule *is*: a run of dates, a week, and the days
that break it.

Four facts and nothing else:

- **a start and an end date** - the run of the exhibition. Outside it the
  piece never starts on its own, whatever the week says.
- **a week** - for each weekday, the hours the piece is live. A weekday
  with no hours is a closing day.
- **exceptionally running dates** - a date that is live although its
  weekday is not, with its own hours. A late opening, a private view.
- **exceptionally standby dates** - a date that is not live although its
  weekday is. A public holiday, a day the room is wanted for something
  else.

**There is deliberately no schedule by default.** Empty rules mean the
piece is started by hand from the page, exactly as it always has been,
and that is what a fresh `params.json` gets. A schedule is something
somebody writes.

**The text form is the way in.** Every other value in this tree is
entered through `ValueSetter2`'s digit drill-down, which is right for a
servo origin and hopeless for seven pairs of times and a list of dates -
so the schedule is edited as text in a textarea, the one mechanism the
page has for that (`leaves.editor`, and see `MarkdownDocument`, which is
the same view/edit/save shape). The *structure* is what lives in
`params.json`, so the params page can show it and a migration can reach
it; this module is the two directions between the two.

**Unreadable is refused, never half-read.** `parse` raises on the first
line it cannot make sense of and names the line number. A schedule that
silently dropped the line it did not understand would be a dark room on a
day somebody thought they had opened, and the mistake would stay
invisible until it happened.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import NamedTuple

# Monday first - as the week is written where this piece is shown, and as
# `date.weekday()` numbers it, so an index into this tuple *is* the
# weekday number and nothing has to translate between the two.
WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)

# The word a weekday line uses to say "not this day". Spelled out rather
# than left as an empty line, because an empty line is also what a
# half-typed schedule looks like, and this has to be a thing somebody
# wrote on purpose.
CLOSED = "closed"

MINUTES_IN_A_DAY = 24 * 60


class ScheduleError(Exception):
    """A schedule that cannot be read, and where.

    Carries the line number when it came from the text form, so the page
    can say "line 7" rather than hand somebody a traceback, and none when
    it came from `params.json` - which is hand-editable too, and whose
    mistakes have to be caught in exactly the same place.
    """

    def __init__(self, message: str, line_number: int | None = None) -> None:
        self.line_number = line_number
        self.message = message
        super().__init__(
            message if line_number is None else f"line {line_number}: {message}"
        )


class Window(NamedTuple):
    """One stretch of one day, in minutes since midnight.

    Minutes rather than `datetime.time` because everything done with these
    is arithmetic - is this moment inside it, how long is it, does it
    overlap its neighbour - and a comparison between two ints is the kind
    of thing that cannot be got subtly wrong. `label` is the only place
    the clock-face form is built back up.
    """

    opens: int
    closes: int

    @property
    def label(self) -> str:
        return f"{minutes_to_clock(self.opens)}-{minutes_to_clock(self.closes)}"

    @property
    def minutes(self) -> int:
        return self.closes - self.opens

    def contains(self, minute_of_day: int) -> bool:
        """Half open: a window closing at 18:00 is shut at 18:00.

        The other convention leaves the piece running for the one minute
        after closing time, every closing time - the kind of small
        wrongness nobody reports and everybody notices.
        """
        return self.opens <= minute_of_day < self.closes


@dataclass(frozen=True)
class Rules:
    """A whole schedule. Empty means there is none."""

    starts_on: date | None = None
    ends_on: date | None = None
    # weekday name -> its windows, always all seven of them - see
    # `complete_week`, which both readers put their result through. An
    # empty tuple is a closing day.
    weekly: dict[str, tuple[Window, ...]] = field(default_factory=dict)
    exceptionally_running: dict[date, tuple[Window, ...]] = field(default_factory=dict)
    exceptionally_standby: tuple[date, ...] = ()

    @property
    def is_empty(self) -> bool:
        """Nothing has been written, so the piece is started by hand."""
        return (
            self.starts_on is None
            and self.ends_on is None
            and not any(self.weekly.values())
            and not self.exceptionally_running
            and not self.exceptionally_standby
        )

    @property
    def has_a_run(self) -> bool:
        """Both ends of the exhibition are known.

        The solver needs both. A schedule with a start and no end is not
        one the piece can be left alone with, because nothing in it ever
        says stop.
        """
        return self.starts_on is not None and self.ends_on is not None


# --- times ---------------------------------------------------------------


def minutes_to_clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def clock_to_minutes(clock: str, line_number: int | None = None) -> int:
    hours, _, rest = clock.partition(":")
    if not rest or not hours.isdigit() or not rest.isdigit():
        raise ScheduleError(f"{clock!r} is not a time - write it as HH:MM", line_number)
    minutes = int(hours) * 60 + int(rest)
    if int(rest) > 59 or minutes > MINUTES_IN_A_DAY:
        raise ScheduleError(f"{clock!r} is not a time on the clock", line_number)
    return minutes


def parse_window(token: str, line_number: int | None = None) -> Window:
    opens, dash, closes = token.partition("-")
    if not dash:
        raise ScheduleError(
            f"{token!r} is not a stretch of hours - write it as HH:MM-HH:MM",
            line_number,
        )
    window = Window(
        clock_to_minutes(opens.strip(), line_number),
        clock_to_minutes(closes.strip(), line_number),
    )
    if window.closes <= window.opens:
        raise ScheduleError(
            f"{token!r} ends before it starts - a stretch running over "
            "midnight has to be written as one piece on each day",
            line_number,
        )
    return window


def parse_windows(
    tokens: list[str], line_number: int | None = None
) -> tuple[Window, ...]:
    """The hours on one line: sorted, with overlaps refused.

    Several are allowed on purpose. A gallery with a lunchtime closing is
    two stretches, and writing it as one would leave the piece moving in
    an empty room for an hour a day.
    """
    parts = " ".join(tokens).replace(",", " ").split()
    if len(parts) == 1 and parts[0].lower() == CLOSED:
        return ()
    if not parts:
        raise ScheduleError(
            f"no hours given - write the hours, or {CLOSED!r}", line_number
        )

    windows = sorted(parse_window(part, line_number) for part in parts)
    for earlier, later in zip(windows, windows[1:]):
        if later.opens < earlier.closes:
            raise ScheduleError(
                f"{earlier.label} and {later.label} overlap", line_number
            )
    return tuple(windows)


def complete_week(weekly: dict[str, tuple[Window, ...]]) -> dict[str, tuple[Window, ...]]:
    """Every weekday present, in week order, closing days included.

    Both readers end here, so a schedule that named three weekdays and
    one that named all seven and closed four of them are the same object.
    They describe the same week, and two `Rules` that describe the same
    week comparing unequal would make every round-trip test in this suite
    a test of which lines somebody happened to type.
    """
    return {day: tuple(weekly.get(day, ())) for day in WEEKDAYS}


def parse_date(token: str, line_number: int | None = None) -> date:
    try:
        return date.fromisoformat(token)
    except ValueError:
        raise ScheduleError(
            f"{token!r} is not a date - write it as YYYY-MM-DD", line_number
        ) from None


# --- the text form -------------------------------------------------------


def parse(text: str) -> Rules:
    """Read a schedule, or say which line stopped you.

    The grammar is five kinds of line and a `#` comment::

        from 2026-09-15
        to   2026-12-20
        tuesday  10:00-18:00
        open   2026-10-05  14:00-18:00
        closed 2026-11-01

    Order does not matter and blank lines are ignored, so the week and
    the exceptions can be grouped however reads best.
    """
    starts_on: date | None = None
    ends_on: date | None = None
    end_line: int | None = None
    weekly: dict[str, tuple[Window, ...]] = {}
    running: dict[date, tuple[Window, ...]] = {}
    standby_lines: dict[date, int] = {}

    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue

        head, *rest = line.split()
        keyword = head.lower()

        if keyword == "from":
            if starts_on is not None:
                raise ScheduleError("the run already has a start date", line_number)
            starts_on = _exactly_one_date(keyword, rest, line_number)

        elif keyword == "to":
            if ends_on is not None:
                raise ScheduleError("the run already has an end date", line_number)
            ends_on = _exactly_one_date(keyword, rest, line_number)
            end_line = line_number

        elif keyword in WEEKDAYS:
            if keyword in weekly:
                raise ScheduleError(f"{keyword} is given twice", line_number)
            weekly[keyword] = parse_windows(rest, line_number)

        elif keyword == "open":
            when, windows = _date_and_windows(rest, line_number)
            if when in running:
                raise ScheduleError(f"{when} is already an open day", line_number)
            running[when] = windows

        elif keyword == CLOSED:
            when = _exactly_one_date(keyword, rest, line_number)
            if when in standby_lines:
                raise ScheduleError(f"{when} is already a standby day", line_number)
            standby_lines[when] = line_number

        else:
            raise ScheduleError(
                f"{head!r} is not something a schedule line can start with - "
                f"expected from, to, a weekday, open or {CLOSED}",
                line_number,
            )

    if starts_on is not None and ends_on is not None and ends_on < starts_on:
        raise ScheduleError(
            f"the run ends ({ends_on}) before it starts ({starts_on})", end_line
        )

    # A date written as both is not a fine point of precedence, it is two
    # sentences that contradict each other. Refusing it here means the
    # solver never has to hold an opinion about which one wins.
    both = sorted(set(running) & set(standby_lines))
    if both:
        raise ScheduleError(
            f"{both[0]} is written as both an open day and a standby day",
            standby_lines[both[0]],
        )

    return Rules(
        starts_on=starts_on,
        ends_on=ends_on,
        weekly=complete_week(weekly),
        exceptionally_running=running,
        exceptionally_standby=tuple(sorted(standby_lines)),
    )


def _exactly_one_date(keyword: str, tokens: list[str], line_number: int) -> date:
    if len(tokens) != 1:
        raise ScheduleError(f"{keyword!r} takes one date and nothing else", line_number)
    return parse_date(tokens[0], line_number)


def _date_and_windows(
    tokens: list[str], line_number: int
) -> tuple[date, tuple[Window, ...]]:
    if not tokens:
        raise ScheduleError("no date given", line_number)
    when = parse_date(tokens[0], line_number)
    if not tokens[1:]:
        raise ScheduleError(
            f"{when} is an open day with no hours - say which hours it runs",
            line_number,
        )
    return when, parse_windows(tokens[1:], line_number)


def format_rules(rules: Rules) -> str:
    """The canonical text for a schedule - what `edit` puts in the box.

    Round-tripping through this loses comments and re-orders the lines
    into the shape above. Worth saying out loud, because it is a real
    cost: the structure in `params.json` is what is kept, and the text is
    a view onto it rather than a file somebody owns.
    """
    lines = [
        "# The exposition schedule.",
        "#",
        "# Times are 24h, on this machine's own clock. A weekday with no",
        f"# hours is written {CLOSED}. Exceptions win over the week.",
        "",
        # Commented out when unset, so the template a fresh installation
        # is handed parses back to the empty schedule it came from. A
        # bare `from YYYY-MM-DD` reads as a filled-in field and refuses to
        # save, which is a poor way to be told to fill something in.
        f"from {rules.starts_on}" if rules.starts_on else "# from YYYY-MM-DD",
        f"to   {rules.ends_on}" if rules.ends_on else "# to   YYYY-MM-DD",
        "",
    ]

    width = max(len(day) for day in WEEKDAYS)
    for day in WEEKDAYS:
        windows = rules.weekly.get(day, ())
        hours = "  ".join(window.label for window in windows) if windows else CLOSED
        lines.append(f"{day.ljust(width)}  {hours}")

    if rules.exceptionally_running or rules.exceptionally_standby:
        lines.extend(["", "# Days that break the week above."])
    for when in sorted(rules.exceptionally_running):
        hours = "  ".join(w.label for w in rules.exceptionally_running[when])
        lines.append(f"open    {when}  {hours}")
    for when in rules.exceptionally_standby:
        lines.append(f"{CLOSED}  {when}")

    return "\n".join(lines) + "\n"


# --- the params form -----------------------------------------------------

# The keys in params.json, spelled as prose like every other key in that
# file, and named here so the node and the defaults cannot drift apart.
ENABLED = "enabled"
STARTS_ON = "starts on"
ENDS_ON = "ends on"
WEEKLY = "weekly"
RUNNING = "exceptional running"
STANDBY = "exceptional standby"


def to_params(rules: Rules) -> dict:
    """The structure to persist.

    `enabled` is deliberately not in here: it is the switch, not the
    schedule, so saving new hours must never be able to turn the piece
    on. Writing one is a separate press.
    """
    return {
        STARTS_ON: rules.starts_on.isoformat() if rules.starts_on else "",
        ENDS_ON: rules.ends_on.isoformat() if rules.ends_on else "",
        WEEKLY: {
            day: [window.label for window in rules.weekly.get(day, ())]
            for day in WEEKDAYS
        },
        RUNNING: {
            when.isoformat(): [window.label for window in windows]
            for when, windows in sorted(rules.exceptionally_running.items())
        },
        STANDBY: [when.isoformat() for when in rules.exceptionally_standby],
    }


def from_params(section) -> Rules:
    """Read the structure back, refusing junk the way `parse` does.

    `params.json` is hand-editable, and strings and lists are read-only
    on the params page, so the way a bad value gets in here is somebody
    with a text editor. It has to fail as a sentence on the schedule's
    own page, not as a `ValueError` out of a request.
    """
    starts_on = _optional_date(section.get(STARTS_ON), STARTS_ON)
    ends_on = _optional_date(section.get(ENDS_ON), ENDS_ON)

    weekly: dict[str, tuple[Window, ...]] = {}
    for day, hours in (section.get(WEEKLY) or {}).items():
        if day.lower() not in WEEKDAYS:
            raise ScheduleError(f"{day!r} under {WEEKLY!r} is not a weekday")
        # An empty list is how the params form spells a closing day, and
        # it is what every weekday starts as. The text form has to say
        # `closed` out loud instead - there a blank line is indis-
        # tinguishable from a half-typed one - so the two forms differ
        # here on purpose and `parse_windows` is only right for one.
        weekly[day.lower()] = parse_windows(list(hours)) if hours else ()

    running: dict[date, tuple[Window, ...]] = {}
    for when, hours in (section.get(RUNNING) or {}).items():
        running[parse_date(when)] = parse_windows(list(hours))

    standby = tuple(sorted(parse_date(when) for when in (section.get(STANDBY) or [])))

    if starts_on is not None and ends_on is not None and ends_on < starts_on:
        raise ScheduleError(f"the run ends ({ends_on}) before it starts ({starts_on})")

    return Rules(
        starts_on=starts_on,
        ends_on=ends_on,
        weekly=complete_week(weekly),
        exceptionally_running=running,
        exceptionally_standby=standby,
    )


def _optional_date(value, key: str) -> date | None:
    if not value:
        return None
    if not isinstance(value, str):
        raise ScheduleError(f"{key!r} should be a date written as YYYY-MM-DD")
    return parse_date(value)
