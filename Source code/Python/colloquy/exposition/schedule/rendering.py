# -*- coding: utf-8 -*-
# Source code/Python/colloquy/exposition/schedule/rendering.py

"""The solved schedule as markup: one row per date of the run.

Classes and no inline styles, like `scenario_browser/rendering.py` - the
installation's stylesheet carries the `.schedule-*` rules and the mock
deliberately carries none, which is the arrangement the two UIs are kept
in. An `html` leaf is the same leaf in both, so this is one renderer
rather than the two a change to the page itself would need.

Rows are marked by *why* they read as they do, not only by whether the
piece runs: a day that is dark because somebody wrote a standby line and
a day that is dark because its weekday is a closing day are the same
outcome and completely different facts, and the one somebody is checking
is nearly always the exception.
"""
from __future__ import annotations

from yattag import Doc

from .rules import Rules
from .solver import (
    EXCEPTIONALLY_RUNNING,
    EXCEPTIONALLY_STANDBY,
    Day,
    day_count,
    exceptions_outside_the_run,
    totals,
)


def _row_class(day: Day) -> str:
    kinds = ["schedule-row"]
    kinds.append("schedule-running" if day.is_running else "schedule-standby")
    if day.reason in (EXCEPTIONALLY_RUNNING, EXCEPTIONALLY_STANDBY):
        kinds.append("schedule-exception")
    return " ".join(kinds)


def render_html(rules: Rules, days: tuple[Day, ...]) -> str:
    """The whole run, expanded.

    `days` is passed in rather than solved here so the caller decides how
    much of a mistyped run to draw - see `solver.MAX_DAYS`.
    """
    doc, tag, text = Doc().tagtext()

    if not rules.has_a_run:
        with tag("p", klass="schedule-empty"):
            text(
                "No run of dates has been written, so there is nothing to "
                "work out. The exposition is started by hand."
            )
        return doc.getvalue()

    counted = totals(days)
    with tag("p", klass="schedule-summary"):
        text(
            f"{rules.starts_on} to {rules.ends_on}: {counted.days} days, "
            f"{counted.running_days} running, {counted.standby_days} on standby, "
            f"{counted.hours:.1f} hours of movement in all."
        )

    total = day_count(rules)
    if len(days) < total:
        with tag("p", klass="schedule-problem"):
            text(
                f"Showing the first {len(days)} of {total} days. A run this "
                "long is usually a mistyped year - check the end date."
            )

    outside = exceptions_outside_the_run(rules)
    if outside:
        with tag("p", klass="schedule-problem"):
            text(
                "These exception dates fall outside the run and do nothing: "
                + ", ".join(str(when) for when in outside)
            )

    with tag("div", klass="schedule"):
        for day in days:
            with tag("div", klass=_row_class(day)):
                with tag("div", klass="schedule-date"):
                    text(str(day.on))
                with tag("div", klass="schedule-weekday"):
                    text(day.weekday)
                with tag("div", klass="schedule-hours"):
                    text(day.hours or "-")
                with tag("div", klass="schedule-reason"):
                    text(day.reason)

    return doc.getvalue()
