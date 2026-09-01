# -*- coding: utf-8 -*-
# Source code/Python/colloquy/exposition/schedule/__init__.py

"""When the exposition runs itself, and when nobody has said.

**The default is no schedule at all.** A fresh `params.json` has an empty
run, an empty week and the switch off, which is exactly the behaviour
this repository has always had: somebody opens the page and presses
start. Everything here is opt-in, and the opting in is one press that
says what it does.

**One switch, not two.** A `BaseThread` normally draws a bare `start`
beside its name, and here that would be a second, unlabelled way to say
the same thing as `enable` - and a way to have the watch running while
the schedule reads "disabled", which is a state nobody could act on. So
`start`/`stop` are popped, for the flasher's reason, and `enable` starts
the watch as well as writing the note. The note is what survives a
restart; `main.py` reads it and starts the watch again or does not.

**It stops only what it started.** If a person started the exposition by
hand outside opening hours, the closing time comes and goes and the
piece keeps running - the page says so in as many words. A technician
kneeling at the rack at nine in the evening is making a decision, and a
clock is not the thing that should overrule it. What this does guarantee
is the other direction: nothing it started is left running past closing.

**It refuses to start the piece against the hardware notes.** Unmounting
the main PCB latches `BaseThread._shutdown`, so nothing could start after
it anyway; unplugging the motors deliberately does *not*
(`hardware/motors/`, and the reason is that the bench goes on being
useful), which means an enabled schedule would cheerfully call `start`
on an installation whose servo bus was never opened, every twenty
seconds, for as long as the chain was out. So both notes are read before
acting and named on the page when they are what is stopping it.

The four parts are split by what they know:

- `rules.py` - what a schedule is, and the two directions between its
  text form and `params.json`.
- `solver.py` - the rules worked out into one row per date.
- `rendering.py` - those rows as markup.
- this file - the node: the switch, the editor, the clock, and the one
  call that starts or stops the piece.
"""
from datetime import datetime
from time import time

from colloquy.base import Base
from colloquy.base_thread import BaseThread
from colloquy.ui import leaves

from . import rules as rules_module
from . import solver
from .rendering import render_html

# The key in params.json. One place, so the node and the defaults cannot
# drift apart.
PARAMS_SECTION = "exposition schedule"

# How often the clock is consulted. Twenty seconds is far finer than any
# opening time is written to and costs nothing - the check is arithmetic
# on a handful of dates, with no I/O in it at all. It is not a minute
# because a minute means an opening can be up to a minute late, and the
# first thing anybody does with a new schedule is stand and watch it.
CHECK_INTERVAL = 20.0


class FullSchedule(Base):
    """The run expanded: every date between the two ends, with its hours.

    A child rather than a leaf on the schedule itself, because a run of a
    few months is a few hundred rows and they would bury the four
    readings somebody actually opens the page for. It is also the answer
    to the only question a written schedule cannot be read for - what
    happens on this particular day - so it is worth its own click.
    """

    @property
    def name(self):
        return "full schedule"

    @property
    def snapshot_children(self):
        return {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        schedule, unreadable = self.owner.read_rules()
        if unreadable is not None:
            leaf("cannot be read", unreadable)
            return states

        days = solver.solve(schedule)
        counted = solver.totals(days)
        leaf("days in the run", solver.day_count(schedule) or "none")
        leaf("running days", counted.running_days)
        leaf("standby days", counted.standby_days)
        leaf("hours of movement", f"{counted.hours:.1f}")

        states["solved"] = leaves.html(path, "solved", render_html(schedule, days))
        return states


class ExpositionSchedule(BaseThread):
    """The clock that starts and stops the exposition, when it is let."""

    # On WITHOUT_SCENARIOS, with the repository watch and for its reason:
    # a scenario says what the piece does in the room, and consulting a
    # clock does nothing in the room at all. What happens when this
    # starts the exposition is `switching-on`, which is already written
    # and already hangs off the thing that does it.
    scenario_names = ()

    def __init__(self, owner):
        super().__init__(owner=owner)

        self._mode = "view"
        self._draft = None
        self._draft_error = None
        self._outcome = None
        self._checked_at = None

        # Did *this* start the piece? The whole of "stops only what it
        # started". An instance latch rather than a note in params, for
        # `hardware/motors`' reason: it is a fact about this run of the
        # process, and a restart genuinely does not know.
        self._started_the_piece = False

        self._full = FullSchedule(owner=self)

        self["save"] = self.save
        self["enable"] = self.enable
        self["disable"] = self.disable
        self["check now"] = self.check_now

    @property
    def name(self):
        return "schedule"

    @property
    def exposition(self):
        return self.owner

    @property
    def params(self):
        return self.colloquy.params

    @property
    def section(self):
        return self.params[PARAMS_SECTION]

    @property
    def is_enabled(self):
        return bool(self.section.get(rules_module.ENABLED, False))

    # --- the schedule itself ---------------------------------------------

    def read_rules(self):
        """The rules as params holds them, and what is wrong with them.

        Returns a pair rather than raising, because every caller here is
        drawing a page and a page that raises is a page nobody can use to
        fix the thing that raised. Empty rules stand in for unreadable
        ones so the rest of the node needs no special case.
        """
        try:
            return rules_module.from_params(self.section), None
        except rules_module.ScheduleError as error:
            return rules_module.Rules(), str(error)

    @property
    def rules(self):
        return self.read_rules()[0]

    def as_text(self):
        return rules_module.format_rules(self.rules)

    # --- the switch -------------------------------------------------------

    def enable(self, request=None):
        """Hand the piece to the clock, and start watching it.

        Refuses rather than pretends when there is nothing to obey: an
        enabled schedule with no dates in it would read as an
        installation under control and behave as one that is not.
        """
        schedule, unreadable = self.read_rules()
        if unreadable is not None:
            self._outcome = f"refused: the schedule cannot be read - {unreadable}"
            return self._outcome
        if not schedule.has_a_run:
            self._outcome = (
                "refused: write a run of dates first - a schedule with no "
                "start and end never says stop"
            )
            return self._outcome

        self.section[rules_module.ENABLED] = True
        self.start(started_by=None)
        self._checked_at = None
        self._outcome = "enabled"
        return self._outcome

    def disable(self, request=None):
        """Take the piece back off the clock.

        Deliberately does not stop a running exposition. Disabling says
        "stop deciding for me", and a show being watched by visitors is
        not something to end as a side effect of a settings change - the
        exposition's own stop link is one click away and says what it
        does.
        """
        self.section[rules_module.ENABLED] = False
        self.stop()
        self._started_the_piece = False
        self._outcome = "disabled - the exposition is started by hand again"
        return self._outcome

    def start_if_enabled(self):
        """What `main.py` calls. A watch nobody switched on watches
        nothing, and a note that survives a restart is the point of
        writing it to params."""
        if self.is_enabled:
            self.start(started_by=None)
            return True
        return False

    # --- acting -----------------------------------------------------------

    def why_not_act(self):
        """Why the piece cannot be started right now, or None.

        Instant, and reading only notes already written down - the same
        arrangement as the flasher's refusals, and for the same reason:
        this runs every twenty seconds and must never be the thing that
        blocks a page.
        """
        hardware = self.colloquy.hardware
        if not hardware.main_pcb.is_mounted:
            return (
                "the main PCB is noted as unmounted, so neither serial link "
                "was opened"
            )
        if not hardware.motors.is_plugged_in:
            return (
                "the motors are noted as unplugged, so the servo bus was "
                "never opened and nothing can move"
            )
        if self.exposition.thread_errors:
            return (
                "the exposition stopped on an error - clear it under "
                "'thread errors' before the schedule can start it again"
            )
        return None

    def apply_now(self, moment=None):
        """Compare the clock with the schedule and act on the difference.

        Returns a sentence when it did something or is refusing to, and
        None when the piece is already in the state the schedule asks
        for - which is almost every call, and which is why the caller
        only records a non-None answer.
        """
        moment = datetime.now() if moment is None else moment

        if not self.is_enabled:
            return "the schedule is disabled"

        schedule, unreadable = self.read_rules()
        if unreadable is not None:
            return f"not acting: the schedule cannot be read - {unreadable}"
        if not schedule.has_a_run:
            return "not acting: no run of dates has been written"

        should_run = solver.is_running_at(schedule, moment)
        running = self.exposition.is_started
        stamp = moment.strftime("%Y-%m-%d %H:%M")

        if should_run and not running:
            refusal = self.why_not_act()
            if refusal is not None:
                return f"not starting the exposition: {refusal}"
            self.exposition.start(started_by=None)
            self._started_the_piece = self.exposition.is_started
            return f"started the exposition at {stamp}"

        if not should_run and running:
            if not self._started_the_piece:
                return (
                    f"outside the schedule since {stamp}, but the exposition "
                    "was started by hand - leaving it alone"
                )
            self.exposition.stop()
            self._started_the_piece = False
            return f"stopped the exposition at {stamp}"

        if not running:
            # It stopped on its own, or was stopped by hand. Either way
            # this is no longer holding anything.
            self._started_the_piece = False
        return None

    def check_now(self, request=None):
        """Consult the clock without waiting for the next tick.

        Cheap enough to do inside the request - it is arithmetic on a few
        dates with no I/O - unlike `Repository.check_now`, which hands
        its network half to the loop thread.
        """
        self._checked_at = time()
        outcome = self.apply_now()
        self._outcome = outcome if outcome is not None else "nothing to change"
        return self._outcome

    # --- the editor -------------------------------------------------------

    def enter_edit(self, request=None):
        self._mode = "edit"
        if self._draft is None:
            self._draft = self.as_text()

    def cancel(self, request=None):
        self._mode = "view"
        self._draft = None
        self._draft_error = None

    def save(self, content):
        """Write a schedule, or say which line stopped you.

        A schedule that failed to parse is kept in the box rather than
        thrown away: whoever typed it is one line from having it right,
        and handing them back the canonical form of the *old* schedule
        would lose the lot.
        """
        try:
            parsed = rules_module.parse(content)
        except rules_module.ScheduleError as error:
            self._draft = content
            self._draft_error = str(error)
            self._mode = "edit"
            self.open()
            return

        section = self.section
        for key, value in rules_module.to_params(parsed).items():
            section[key] = value

        self._draft = None
        self._draft_error = None
        self._mode = "view"
        self._outcome = "schedule saved"
        self.open()

    # --- the thread -------------------------------------------------------

    def setup(self):
        self.log(f"Watching the clock every {CHECK_INTERVAL}s.")
        self._checked_at = None

    def loop(self):
        now = time()
        if self._checked_at is not None and now - self._checked_at < CHECK_INTERVAL:
            return
        self._checked_at = now

        outcome = self.apply_now()
        if outcome is not None:
            self._outcome = outcome
            self.log(outcome)

    def setdown(self):
        """Deliberately empty.

        Stopping the watch is not stopping the show. If the piece is
        live, it stays live - the same reasoning as `disable`, and the
        exposition's own stop link is right there.
        """

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        return {self._full.name: self._full}

    def _right_now(self, schedule, moment):
        """One line for the state of the room, and when it changes."""
        if not schedule.has_a_run:
            return "no schedule - started by hand"

        running = solver.is_running_at(schedule, moment)
        state = "within opening hours" if running else "outside opening hours"

        change = solver.next_change(schedule, moment)
        if change is None:
            return f"{state} - and nothing further is scheduled"
        at, running_after = change
        what = "opens" if running_after else "closes"
        return f"{state} - {what} {at.strftime('%a %d %b %H:%M')}"

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)

        # A watch is switched on by `enable`, which says what it does.
        # The bare pair would be a second switch saying nothing, and one
        # that could leave the page reading "disabled" while the clock
        # went on starting the piece.
        states.pop("start", None)
        states.pop("stop", None)

        if self._mode == "edit":
            if self._draft_error is not None:
                leaves.into(states, path)("not saved", self._draft_error)
            states["cancel"] = self.cancel
            states["editor"] = leaves.editor(path, "editor", self._draft or "")
            return states

        moment = datetime.now()
        schedule, unreadable = self.read_rules()
        leaf = leaves.into(states, path)

        if unreadable is not None:
            leaf("cannot be read", unreadable)
            leaf("state", "not acting on an unreadable schedule")
        else:
            leaf("state", "enabled" if self.is_enabled else "disabled")
            leaf("watching", "yes" if self.is_started else "no")
            leaf("runs from", schedule.starts_on or "not set")
            leaf("runs to", schedule.ends_on or "not set")
            leaf("right now", self._right_now(schedule, moment))

        leaf(
            "the exposition",
            "running" if self.exposition.is_started else "stopped",
        )
        if self.exposition.is_started:
            leaf(
                "started by",
                "this schedule" if self._started_the_piece else "hand",
            )

        refusal = self.why_not_act()
        if refusal is not None:
            leaf("cannot start the piece", refusal)
        if self._outcome is not None:
            leaf("last", self._outcome)

        states["enable"] = self.enable
        states["disable"] = self.disable
        states["check now"] = self.check_now
        states["edit"] = self.enter_edit
        states["written"] = leaves.pre(path, "written", self.as_text())
        return states
