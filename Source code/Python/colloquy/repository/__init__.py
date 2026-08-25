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
"""
from threading import Lock
from time import time

from colloquy.base_thread import BaseThread
from colloquy.ui import leaves
from colloquy.utils import timelap_to_string

from .git import Git, GitError, Status

# Every five minutes. The thing being watched is somebody else's git push,
# which happens a handful of times a day at best, so this is already far
# oftener than it needs to be - and each check is one network round trip.
CHECK_INTERVAL = 300


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

    def __init__(self, owner, git: Git | None = None):
        super().__init__(owner=owner)
        self._git = git if git is not None else Git()

        # Written by the polling thread, read by whichever thread is
        # rendering the page. Each is replaced whole rather than mutated,
        # so a render sees one or the other and never a half-built one.
        self._status: Status | None = None
        self._error: str | None = None
        self._checked_at: float | None = None
        self._pull_report: str | None = None
        self._needs_restart = False
        self._pull_asked = False

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
    def needs_restart(self):
        return self._needs_restart

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
            return

        if time() < self._due_at:
            return
        self.check()

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

    def _why_not_pull(self):
        """Why a pull would be a bad idea, or None if it would not.

        The three refusals are things git would also refuse, and
        deliberately not left to it: `pull --ff-only` onto a tree with
        edits in it fails with a wall of git's own prose about local
        changes being overwritten, and the reader on the page wants one
        line telling them to commit first.
        """
        status = self._status
        if status is None:
            return "nothing checked yet - check now first"

        if status.dirty:
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

    def _pull_now(self):
        """The network half. Runs on the loop thread, or on whoever asked
        when there is no loop running."""
        # Asked for on one thread and done on another, so the answer may
        # have changed in between - a check could have run, or the tree
        # been edited. Cheap to ask again, and the alternative is pulling
        # over somebody's uncommitted work.
        refusal = self._why_not_pull()
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

        if self._checked_at is None:
            leaf("last checked", "never")
        else:
            leaf("last checked", f"{timelap_to_string(time() - self._checked_at)} ago")

        if self.is_started:
            due_in = max(0.0, self._due_at - time())
            leaf("next check", f"in {timelap_to_string(due_in)}")
        else:
            leaf("next check", "not watching - start it, or use check now")

        if self._pull_report is not None:
            leaf("last pull", self._pull_report)

        if self._needs_restart:
            leaf(
                "restart",
                "new code is on disk but not running - use restart at the top of the page",
            )

        return states


def _commits(count):
    return f"{count} commit" if count == 1 else f"{count} commits"


def _files(count):
    return f"{count} file" if count == 1 else f"{count} files"
