# -*- coding: utf-8 -*-
# Source code/Python/colloquy/repository/__init__.py

"""Does origin have anything we have not got? Asked every few minutes.

This repo is worked on from two computers, and the failure it exists to
prevent is the quiet one: a machine spends a fortnight editing on top of
a tree the other machine moved past a fortnight ago, and the two only
find out at a merge nobody wanted. Nothing about that is visible from
inside the running program, so it goes on the page beside everything else
about the state of the installation.

What it does by itself is *only* `git fetch` - that writes nothing but
`.git/refs/remotes`, so it cannot disturb a running exhibition, and it is
the whole of what is needed to answer the question. What it never does by
itself is merge. When origin is ahead the page grows a `pull` link and
says so, and somebody decides; see `git.py` for why that pull is
`--ff-only`.

**A pull does not change the code that is running.** Python read the
modules at startup, so the process goes on running the old ones until it
is restarted - which the page already offers, at the top, under
`restart`. The reading says so after a pull that moved, because the
otherwise-reasonable reading of a successful pull is that the new code is
now in.

**On the installation's own laptop, and nowhere else, both of those are
done for it** (2026-10-11). That machine is the one nobody edits on and
the one nobody is sitting at: what it runs is whatever was last pulled by
somebody who happened to be in the room, and with the main PCB out for
replacement the files it hands out - the Gerbers, the KiCad projects -
are only as new as that. So there it looks once a minute instead of once
in five, pulls the moment origin has something it can fast-forward to,
and asks the server to restart onto the new code. Three things keep that
from being the thing the paragraphs above warn about:

- **It is still `--ff-only`.** The pull is the same command the link
  runs. A branch that has diverged is not pulled, by anybody.
- **It never restarts under a running piece.** A restart stops every
  thread and starts none, so pulling the floor from under an exhibition
  somebody started by hand would leave it dark until they came back. The
  restart waits for `drivers` and `tests` to be idle, and the page says
  what it is waiting for.
- **It says what it is doing while it does it.** `notice` is one sentence
  for a banner on every page - pulling, about to restart, waiting, cannot
  - and the restart is announced `RESTART_NOTICE` seconds before it
  happens rather than discovered as a page that stopped answering.

Every other machine is somebody's working tree, where a pull nobody
asked for is exactly the accident this node exists to prevent.
"""
import os
from datetime import datetime
from threading import Lock
from time import time
from typing import NamedTuple

from colloquy import machines
from colloquy.base_thread import BaseThread
from colloquy.ui import leaves
from colloquy.utils import timelap_to_string

from .git import Git, GitError, Status

# Every five minutes. The thing being watched is somebody else's git push,
# which happens a handful of times a day at best, so this is already far
# oftener than it needs to be - and each check is one network round trip.
CHECK_INTERVAL = 300

# Where the pull is automatic, the interval is the whole of the wait
# between a push and the laptop having it, so it is as short as one
# fetch a minute against a hosted remote can decently be.
AUTO_CHECK_INTERVAL = 60

# How long the page says "restarting" before it does. Long enough for a
# page that polls every few seconds to have said so at least twice.
RESTART_NOTICE = 15.0

# For how long after an automatic restart the page goes on saying that
# one happened - somebody coming back to a page that reloaded itself
# should be able to find out why.
UPDATED_NOTICE = 600.0

# What must be idle before the server may be restarted under it: the
# threads that drive the piece, and a hardware test in the middle of a
# run. Filed by where a thread hangs in the tree, the flasher's
# `IN_THE_WAY` and for its reason - "anything running" would include this
# watch, and the schedule's.
IN_THE_WAY = ("drivers", "tests")

# How the process that restarts tells the process it becomes that it did.
# An environment variable survives an exec and nothing else here does.
UPDATED_FROM = "COLLOQUY_UPDATED_FROM"


class Notice(NamedTuple):
    """What an automatic update is doing, as a banner would say it."""

    # pulling / restarting / waiting / stopped / blocked / updated
    phase: str
    text: str
    # Seconds until the restart, while one is being counted down to.
    restart_in: float | None = None


class Repository(BaseThread):
    """The git checkout the program is running out of, as a node.

    Started by main.py rather than by a click, because a watch nobody
    remembers to switch on is a watch that reports nothing. It is also
    stoppable and startable from the page like any other thread, and
    stopping it costs nothing but the polling.
    """

    # No scenario, and there will not be one: a scenario describes what
    # the piece does in the room, and this does nothing in the room at
    # all. See pytest_tests/test_scenarios.py, which knows.
    scenario_names = ()

    interval = CHECK_INTERVAL

    def __init__(
        self,
        owner,
        git: Git | None = None,
        auto_update: bool | None = None,
        updated_from: str | None = None,
    ):
        super().__init__(owner=owner)
        self._git = git if git is not None else Git()

        # Which machine this is decides it, and nothing on the page can
        # change it: a switch would be a way to turn automatic pulls on
        # over somebody's working tree.
        if auto_update is None:
            auto_update = machines.is_installation()
        self._auto_update = bool(auto_update)
        if self._auto_update:
            self.interval = AUTO_CHECK_INTERVAL

        # Written by the polling thread, read by whichever thread is
        # rendering the page. Each is replaced whole rather than mutated,
        # so a render sees one or the other and never a half-built one.
        self._status: Status | None = None
        self._error: str | None = None
        self._checked_at: float | None = None
        self._pull_report: str | None = None
        self._needs_restart = False
        self._pull_asked = False

        # The commit that was checked out when this process first looked,
        # which is the code it is running. A checkout that is no longer
        # on it has moved under the process - by this node's own pull, or
        # by somebody typing `git pull` in a terminal, which is the same
        # fact and deserves the same answer.
        self._running: str | None = None
        self._pulling: str | None = None
        self._restart_at: float | None = None

        # Set by the process this one replaced, when the restart was one
        # it gave itself. Taken out of the environment so a later restart
        # by hand does not inherit the claim.
        if updated_from is None:
            updated_from = os.environ.pop(UPDATED_FROM, None)
        self._updated_from = updated_from or None
        self._born_at = time()

        # A fetch from the loop and a pull from a page request are two
        # threads reaching for the same working copy. git would sort it
        # out with its own locks, but it would do so by failing one of
        # them with an index.lock error that means nothing to a reader.
        self._git_lock = Lock()
        self._due_at = 0.0

        self["check now"] = self.check_now
        self["pull"] = self.pull

    @property
    def name(self):
        return "repository"

    @property
    def git(self):
        return self._git

    @property
    def status(self):
        """The last reading, or None if none has been taken."""
        return self._status

    @property
    def error(self):
        """Why the last check failed, or None if it did not."""
        return self._error

    @property
    def auto_update(self):
        """Does this machine pull and restart by itself?"""
        return self._auto_update

    @property
    def running(self):
        """The commit this process is running, or None before the first
        check has said."""
        return self._running

    @property
    def needs_restart(self):
        """Is the code on disk no longer the code that is running?"""
        if self._needs_restart:
            return True
        status = self._status
        return (
            status is not None
            and self._running is not None
            and bool(status.head)
            and status.head != self._running
        )

    # --- the check ------------------------------------------------------

    def check(self):
        """Fetch, then read where we stand. Never raises.

        Both halves are one operation as far as the page is concerned, so
        a failure in either leaves the same thing behind: an error to
        show, and the previous status kept rather than blanked - knowing
        we were 3 behind at 14:05 beats knowing nothing.
        """
        with self._git_lock:
            try:
                self._git.fetch()
                self._status = self._git.status()
                self._error = None
                if self._running is None:
                    self._running = self._status.head or None
            except GitError as error:
                self._error = str(error)
            finally:
                self._checked_at = time()
                self._due_at = self._checked_at + self.interval

        return self._status

    def check_now(self, request=None):
        """The page asking for a check this second.

        When the thread is running, hand it the job rather than doing it
        here: a fetch can sit on a dead network for a minute, and the
        request that clicked this is holding the browser open the whole
        time. With no thread running there is nobody to hand it to, so do
        it inline - somebody who clicked it is willing to wait.
        """
        if self.is_started:
            self._due_at = 0.0
            return
        self.check()

    def setup(self):
        self._due_at = 0.0

    def loop(self):
        # A pull that has been asked for goes first: somebody is watching
        # the page waiting for it, and a check would only delay it.
        if self._pull_asked:
            self._pull_asked = False
            self._pull_now()
        elif time() >= self._due_at:
            self.check()
            if self._auto_update:
                self._pull_by_itself()

        if self._auto_update:
            self._count_down_to_restart()

    def setdown(self):
        # Nothing to release: every git call is a subprocess that has
        # already exited by the time it returns.
        pass

    # --- the pull -------------------------------------------------------

    def pull(self, request=None):
        """Fast-forward onto origin, if that is a thing that can be done.

        Refuse here, but do the work over there. The refusals are instant
        - they only read the last status, no git and no network - so the
        reader gets told straight away why nothing is going to happen.
        The pull itself is a network round trip that can sit on a dead
        connection for a minute, and it must not do that inside a request:
        `Colloquy.get_states` holds one lock for the whole application, so
        a minute in here is a minute in which no page in the tree answers.
        Hand it to the loop, exactly as `check_now` does.
        """
        refusal = self._why_not_pull()
        if refusal is not None:
            self._pull_report = refusal
            return refusal

        if self.is_started:
            self._pull_asked = True
            self._pull_report = "pulling - refresh in a moment"
            return self._pull_report

        # Nobody to hand it to. Somebody who stopped the watch and then
        # clicked pull is willing to wait for it.
        return self._pull_now()

    def _why_not_pull(self, automatic=False):
        """Why a pull would be a bad idea, or None if it would not.

        The three refusals are things git would also refuse, and
        deliberately not left to it: `pull --ff-only` onto a tree with
        edits in it fails with a wall of git's own prose about local
        changes being overwritten, and the reader on the page wants one
        line telling them to commit first.

        **The automatic pull does not refuse over a dirty tree, and that
        is not a relaxation of the safety.** `--ff-only` never overwrites
        an uncommitted change: where an incoming commit touches a file
        that has one, git refuses the whole pull and touches nothing.
        What the refusal here adds for a person is a better sentence, and
        a moment to notice that the edits may be the other computer's.
        What it would add for the installation's laptop is an update that
        stops for good the first time a stray file appears in a folder
        nobody is looking at, with nobody there to read why.
        """
        status = self._status
        if status is None:
            return "nothing checked yet - check now first"

        if status.dirty and not automatic:
            return (
                f"{_files(status.dirty)} changed here and not committed - "
                "commit or stash them first, they may be the other computer's work"
            )

        if not status.is_behind:
            return f"nothing to pull: {status.upstream} has nothing new"

        if not status.can_fast_forward:
            return (
                f"{_commits(status.behind)} on {status.upstream} and "
                f"{_commits(status.ahead)} here that it has not got - "
                "that is a merge, and it wants doing by hand"
            )

        return None

    def _pull_now(self, automatic=False):
        """The network half. Runs on the loop thread, or on whoever asked
        when there is no loop running."""
        # Asked for on one thread and done on another, so the answer may
        # have changed in between - a check could have run, or the tree
        # been edited. Cheap to ask again, and the alternative is pulling
        # over somebody's uncommitted work.
        refusal = self._why_not_pull(automatic=automatic)
        if refusal is not None:
            self._pull_report = refusal
            return refusal

        # _why_not_pull() refuses on a missing status, so there is one
        # here. Spelled out rather than assumed: it is the kind of
        # implication that survives until somebody reorders the refusals.
        status = self._status
        assert status is not None
        behind = status.behind

        with self._git_lock:
            try:
                answer = self._git.pull()
                self._needs_restart = True
                self._pull_report = answer or f"pulled {_commits(behind)}"
            except GitError as error:
                self._pull_report = f"pull failed: {error}"
                return self._pull_report

        # Straight away, so the next render shows where we now stand
        # rather than the state that made the link appear.
        self.check()
        return self._pull_report

    # --- by itself, on the installation ----------------------------------

    def _pull_by_itself(self):
        """Pull what the check just found, if it can be fast-forwarded to.

        Called straight after a check, on the loop thread, so there is
        nothing to hand off and nothing a request waits on.
        """
        status = self._status
        if self._error is not None or status is None or not status.can_fast_forward:
            return

        # Set before the pull and cleared after it, so a page drawn
        # during the network round trip says what is happening.
        self._pulling = _commits(status.behind)
        self.log(f"{status.upstream} has {self._pulling} - pulling.")
        try:
            report = self._pull_now(automatic=True)
        finally:
            self._pulling = None
        self.log(f"Automatic pull: {report}")

    def _count_down_to_restart(self):
        """Start the clock the first time the code on disk is not the
        code that is running. It is never restarted: the server does the
        restart when the clock runs out and nothing is in the way, and a
        clock that began again at every tick would never run out."""
        if self._restart_at is None and self.needs_restart:
            self._restart_at = time() + RESTART_NOTICE
            self.log("New code is on disk - the server will restart to run it.")

    def threads_in_the_way(self):
        """Running threads a restart would stop without starting again.

        Read off a copy of the set rather than through `all_threads`:
        that property prunes the shared set while it reads it, and this
        is asked from the server's accept loop twice a second while
        request threads are walking the same set.
        """
        return [
            thread
            for thread in list(self._all_threads)
            if thread is not self
            and thread.is_started
            and thread.path.parts
            and thread.path.parts[0] in IN_THE_WAY
        ]

    @property
    def _is_watching(self):
        """Is the loop alive, and has nobody stopped the installation?

        An emergency stop latches `_shutdown`, and a server that then
        restarted itself onto new code would be undoing the one press
        whose whole meaning is that nothing starts again until a person
        says so.
        """
        return self.is_started and not self._shutdown.is_set()

    @property
    def restart_is_due(self):
        """Should the server restart now? Asked by its accept loop.

        The tree holds no way to restart the server - `Colloquy` has had
        no `request_stop` since unmounting became a route - so this is a
        question the server asks rather than a call the node makes.
        """
        if not self._auto_update or self._restart_at is None:
            return False
        if not self._is_watching:
            return False
        if time() < self._restart_at:
            return False
        return not self.threads_in_the_way()

    def restarting(self):
        """The server saying it is about to restart for this update.

        Leaves the note the next process reads to say what happened - see
        `UPDATED_FROM`.
        """
        os.environ[UPDATED_FROM] = self._running or "an earlier commit"

    @property
    def notice(self):
        """What the update is doing, or None when there is nothing to say.

        One sentence for every page, because an update that restarts the
        server is something a person at any page is about to be affected
        by. Quiet when all is well: a banner that is always there is a
        banner nobody reads.
        """
        if not self._auto_update:
            return None

        status = self._status

        if self._pulling is not None:
            upstream = status.upstream if status is not None else "origin"
            return Notice(
                "pulling",
                f"Updating: pulling {self._pulling} from {upstream}. "
                "The server will restart by itself to run the new code.",
            )

        if self._restart_at is not None:
            if not self._is_watching:
                return Notice(
                    "stopped",
                    "An update is on disk, but the installation has been "
                    "stopped, so it will not restart by itself. Press "
                    "restart to run the new code.",
                )
            busy = self.threads_in_the_way()
            if busy:
                names = ", ".join(sorted(thread.path.as_posix() for thread in busy)[:3])
                return Notice(
                    "waiting",
                    f"An update is on disk and not running yet. The server "
                    f"restarts by itself as soon as this stops: {names}. "
                    "Press restart to do it now.",
                )
            return Notice(
                "restarting",
                "An update has been pulled. The server is restarting by "
                "itself to run it - this page comes back in a few seconds.",
                max(0.0, self._restart_at - time()),
            )

        stuck = self._why_stuck()
        if stuck is not None:
            return Notice("blocked", f"Cannot update by itself: {stuck}")

        if self._updated_from is not None and time() - self._born_at < UPDATED_NOTICE:
            at = datetime.fromtimestamp(self._born_at).strftime("%H:%M")
            now = f", now running {self._running}" if self._running else ""
            return Notice(
                "updated",
                f"Updated and restarted by itself at {at}: "
                f"was {self._updated_from}{now}.",
            )

        return None

    def _why_stuck(self):
        """Why origin is ahead and staying ahead, or None if it is not."""
        status = self._status
        if status is None or not status.is_behind:
            return None
        if not status.can_fast_forward:
            return self._why_not_pull(automatic=True)
        report = self._pull_report
        if report is not None and report.startswith("pull failed"):
            return report
        return None

    # --- what the page draws --------------------------------------------

    @property
    def summary(self):
        """The one line worth reading, whatever else is on the node."""
        if self._error is not None:
            return f"could not check: {self._error}"

        status = self._status
        if status is None:
            return "not checked yet"

        if status.can_fast_forward:
            return f"{_commits(status.behind)} to pull from {status.upstream}"

        if status.is_behind:
            return (
                f"{_commits(status.behind)} on {status.upstream}, "
                f"{_commits(status.ahead)} here it has not got"
            )

        if status.ahead:
            return f"{_commits(status.ahead)} to push to {status.upstream}"

        return f"up to date with {status.upstream}"

    @property
    def last_checked(self):
        """When it last looked, as the page says it."""
        if self._checked_at is None:
            return "never"
        return f"{timelap_to_string(time() - self._checked_at)} ago"

    @property
    def snapshot_children(self):
        """Two commands and no children.

        `pull` appears only when origin actually has something, because
        that appearing *is* the proposal - the node is quiet until there
        is a reason not to be. It still refuses for itself when clicked,
        since a page can sit open across a check that changes the answer.
        """
        children = {"check now": self.check_now}
        status = self._status
        if status is not None and status.is_behind:
            children["pull"] = self.pull
        return self._with_scenarios(children)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        leaf("summary", self.summary)

        status = self._status
        if status is not None:
            leaf("branch", f"{status.branch} -> {status.upstream}")
            leaf("behind", f"{status.behind}")
            leaf("ahead", f"{status.ahead}")
            leaf("working tree", "clean" if not status.dirty else _files(status.dirty))
            leaf("newest on origin", status.newest)

        if self._running is not None:
            leaf("running", self._running)

        leaf("last checked", self.last_checked)

        if self.is_started:
            due_in = max(0.0, self._due_at - time())
            leaf("next check", f"in {timelap_to_string(due_in)}")
        else:
            leaf("next check", "not watching - start it, or use check now")

        if self._auto_update:
            leaf(
                "automatic updates",
                "on - this is the installation's laptop: it pulls what "
                "origin has and restarts onto it without being asked",
            )
        else:
            leaf(
                "automatic updates",
                f"off - only {machines.INSTALLATION} pulls by itself; "
                "here it is a link",
            )

        if self._pull_report is not None:
            leaf("last pull", self._pull_report)

        notice = self.notice
        if notice is not None:
            leaf("update", notice.text)
        elif self.needs_restart:
            leaf(
                "restart",
                "new code is on disk but not running - use restart at the top of the page",
            )

        return states


def _commits(count):
    return f"{count} commit" if count == 1 else f"{count} commits"


def _files(count):
    return f"{count} file" if count == 1 else f"{count} files"
