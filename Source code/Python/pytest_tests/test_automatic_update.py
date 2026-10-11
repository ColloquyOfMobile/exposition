# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/test_automatic_update.py

"""The installation's laptop pulling and restarting by itself.

Everywhere else `Repository` only fetches, and `test_repository.py` holds
it to that. On the one machine nobody edits on and nobody sits at, it
also pulls what it can fast-forward to and asks the server to restart
onto it. What is pinned here is everything that keeps that from being
the accident the node was written to prevent: which machine it happens
on, that it is still only ever a fast-forward, that it never restarts
under a running piece or after an emergency stop, and that a page can
say what is going on at every step of it.

No git, no thread and no clock: `Git` is a double, the loop is called by
hand, and the countdown is moved rather than waited for.
"""
import os
from threading import Event
from time import time
from types import SimpleNamespace

import pytest

from colloquy import machines
from colloquy.base import Base
from colloquy.base_thread import BaseThread
from colloquy.repository import (
    AUTO_CHECK_INTERVAL,
    CHECK_INTERVAL,
    RESTART_NOTICE,
    UPDATED_FROM,
    UPDATED_NOTICE,
    Repository,
)
from colloquy.repository.git import REPO_FOLDER, GitError, Status

OLD = "aaa1111 the code that is running"
NEW = "bbb2222 the code origin has"


def status(behind=0, ahead=0, dirty=0, head=OLD):
    return Status(
        branch="Refactor",
        upstream="origin/Refactor",
        behind=behind,
        ahead=ahead,
        dirty=dirty,
        newest=NEW,
        head=head,
    )


class FakeGit:
    """A checkout that is behind until it is pulled."""

    def __init__(self, before, after=None, fetch_error=None, pull_error=None):
        self._status = before
        self._after = after if after is not None else status(head=NEW)
        self.fetch_error = fetch_error
        self.pull_error = pull_error
        self.pulled = 0
        self.during_pull = None

    def fetch(self):
        if self.fetch_error is not None:
            raise GitError(self.fetch_error)

    def status(self):
        return self._status

    def pull(self):
        self.pulled += 1
        if self.during_pull is not None:
            self.during_pull()
        if self.pull_error is not None:
            raise GitError(self.pull_error)
        self._status = self._after
        return "Fast-forward"


class Watching(Repository):
    """A repository whose watch is running, without running one - the
    suite never starts a thread (conftest)."""

    @property
    def is_started(self):
        return True


def make(git, auto_update=True, updated_from="", kind=Watching):
    owner = SimpleNamespace(owners=[], path=REPO_FOLDER, name="colloquy")
    repository = kind(
        owner=owner, git=git, auto_update=auto_update, updated_from=updated_from
    )
    repository._log = lambda *args, **kwargs: None
    return repository


@pytest.fixture(autouse=True)
def nothing_running(monkeypatch):
    """No thread anywhere, and nobody has stopped the installation."""
    monkeypatch.setattr(Base, "_all_threads", set())
    monkeypatch.setattr(BaseThread, "_shutdown", Event())
    monkeypatch.delenv(UPDATED_FROM, raising=False)


class FakeThread:
    """What `threads_in_the_way` reads of a thread: where it hangs, and
    whether it is alive. A plain class, since it has to go in a set."""

    def __init__(self, path):
        self.path = SimpleNamespace(
            parts=tuple(path.split("/")), as_posix=lambda: path
        )
        self.is_started = True


def a_thread(path):
    return FakeThread(path)


def past_the_notice(repository):
    repository._restart_at = time() - 1


# --- which machine -------------------------------------------------------


def test_only_the_installation_updates_itself(monkeypatch):
    owner = SimpleNamespace(owners=[], path=REPO_FOLDER, name="colloquy")

    monkeypatch.setattr(machines, "hostname", lambda: "somebodys-desk")
    assert Repository(owner=owner, git=FakeGit(status())).auto_update is False

    monkeypatch.setattr(machines, "hostname", lambda: machines.INSTALLATION)
    assert Repository(owner=owner, git=FakeGit(status())).auto_update is True


def test_it_looks_oftener_where_looking_is_the_whole_wait():
    assert make(FakeGit(status()), auto_update=False).interval == CHECK_INTERVAL
    assert make(FakeGit(status())).interval == AUTO_CHECK_INTERVAL
    assert AUTO_CHECK_INTERVAL < CHECK_INTERVAL


# --- the pull ------------------------------------------------------------


def test_it_pulls_without_being_asked():
    git = FakeGit(status(behind=3))
    repository = make(git)

    repository.loop()

    assert git.pulled == 1
    assert repository.needs_restart is True


def test_everywhere_else_it_still_only_fetches():
    """The rule this whole node was built on, on every machine that is
    somebody's working tree."""
    git = FakeGit(status(behind=3))
    repository = make(git, auto_update=False)

    repository.loop()

    assert git.pulled == 0
    assert repository.notice is None
    assert repository.restart_is_due is False


def test_it_never_merges():
    git = FakeGit(status(behind=3, ahead=2))
    repository = make(git)

    repository.loop()

    assert git.pulled == 0
    assert repository.notice.phase == "blocked"
    assert "wants doing by hand" in repository.notice.text


def test_stray_files_do_not_stop_it():
    """`--ff-only` never overwrites an uncommitted change - where one is
    in the way git refuses the whole pull - so dirt alone is not a reason
    for the laptop to stay behind with nobody there to read why."""
    git = FakeGit(status(behind=3, dirty=2))
    repository = make(git)

    repository.loop()

    assert git.pulled == 1


def test_a_person_pressing_pull_is_still_told_about_them():
    git = FakeGit(status(behind=3, dirty=2))
    repository = make(git)
    repository.check()

    assert "not committed" in repository.pull()
    assert git.pulled == 0


def test_a_pull_git_refuses_is_said_and_nothing_restarts():
    git = FakeGit(
        status(behind=3, dirty=1),
        pull_error="error: Your local changes would be overwritten by merge",
    )
    repository = make(git)

    repository.loop()

    assert repository.needs_restart is False
    assert repository.restart_is_due is False
    assert repository.notice.phase == "blocked"
    assert "would be overwritten" in repository.notice.text


def test_no_network_is_an_ordinary_day():
    git = FakeGit(status(behind=3), fetch_error="could not resolve host")
    repository = make(git)

    repository.loop()

    assert git.pulled == 0
    assert repository.notice is None


def test_the_page_says_so_while_the_pull_is_in_the_air():
    git = FakeGit(status(behind=3))
    repository = make(git)
    seen = []
    git.during_pull = lambda: seen.append(repository.notice)

    repository.loop()

    (during,) = seen
    assert during.phase == "pulling"
    assert "3 commits" in during.text and "origin/Refactor" in during.text
    assert repository.notice.phase != "pulling"


# --- the restart ---------------------------------------------------------


def test_the_restart_is_announced_before_it_happens():
    repository = make(FakeGit(status(behind=3)))

    repository.loop()

    notice = repository.notice
    assert notice.phase == "restarting"
    assert 0 < notice.restart_in <= RESTART_NOTICE
    assert repository.restart_is_due is False


def test_then_it_is_due():
    repository = make(FakeGit(status(behind=3)))
    repository.loop()

    past_the_notice(repository)

    assert repository.restart_is_due is True
    assert repository.notice.restart_in == 0


def test_the_clock_is_not_started_again_by_looking_again():
    """The loop runs a hundred times a second. A countdown that began
    again each time would never run out."""
    repository = make(FakeGit(status(behind=3)))
    repository.loop()
    started = repository._restart_at

    repository.loop()
    repository.loop()

    assert repository._restart_at == started


def test_nothing_is_due_when_nothing_changed():
    repository = make(FakeGit(status()))

    repository.loop()
    repository._restart_at = None

    assert repository.needs_restart is False
    assert repository.restart_is_due is False
    assert repository.notice is None


def test_a_checkout_moved_by_hand_is_the_same_fact():
    """Somebody typing `git pull` in a terminal on the laptop leaves new
    code on disk and old code running, exactly as this node's own pull
    does."""
    git = FakeGit(status())
    repository = make(git)
    repository.loop()
    assert repository.running == OLD

    git._status = status(head=NEW)
    repository.check()
    repository.loop()

    assert repository.needs_restart is True
    assert repository.notice.phase == "restarting"


@pytest.mark.parametrize("path", ["drivers", "drivers/female1/search", "tests/autotests/test search"])
def test_it_does_not_restart_under_a_running_piece(monkeypatch, path):
    """A restart stops every thread and starts none. Under an exhibition
    somebody started by hand, that is the piece dark until they return."""
    repository = make(FakeGit(status(behind=3)))
    repository.loop()
    past_the_notice(repository)
    monkeypatch.setattr(Base, "_all_threads", {a_thread(path)})

    assert repository.restart_is_due is False
    notice = repository.notice
    assert notice.phase == "waiting"
    assert path in notice.text


@pytest.mark.parametrize("path", ["repository", "exposition/schedule"])
def test_the_watches_are_not_in_the_way(monkeypatch, path):
    """They run for the whole life of the process. Counting them would
    mean it never restarted at all - the flasher's lesson."""
    repository = make(FakeGit(status(behind=3)))
    repository.loop()
    past_the_notice(repository)
    monkeypatch.setattr(Base, "_all_threads", {a_thread(path)})

    assert repository.restart_is_due is True


def test_a_thread_that_has_stopped_is_not_in_the_way(monkeypatch):
    repository = make(FakeGit(status(behind=3)))
    repository.loop()
    past_the_notice(repository)
    finished = a_thread("drivers")
    finished.is_started = False
    monkeypatch.setattr(Base, "_all_threads", {finished})

    assert repository.restart_is_due is True


def test_it_does_not_undo_an_emergency_stop():
    """The stop latches `_shutdown`, and a server that then restarted
    itself onto new code would be starting the installation again after
    the one press that means nothing starts until a person says so."""
    repository = make(FakeGit(status(behind=3)))
    repository.loop()
    past_the_notice(repository)

    BaseThread._shutdown.set()

    assert repository.restart_is_due is False
    assert repository.notice.phase == "stopped"


def test_it_does_not_restart_when_the_watch_is_not_running():
    repository = make(FakeGit(status(behind=3)), kind=Repository)
    repository.check()
    repository._pull_by_itself()
    repository._count_down_to_restart()
    past_the_notice(repository)

    assert repository.needs_restart is True
    assert repository.restart_is_due is False


# --- afterwards ----------------------------------------------------------


def test_the_next_process_is_told_it_was_an_update():
    repository = make(FakeGit(status(behind=3)), updated_from=None)
    repository.loop()

    repository.restarting()

    assert os.environ[UPDATED_FROM] == OLD


def test_and_says_so_for_a_while():
    repository = make(FakeGit(status(head=NEW)), updated_from=OLD)
    repository.loop()

    notice = repository.notice
    assert notice.phase == "updated"
    assert OLD in notice.text and NEW in notice.text

    repository._born_at = time() - UPDATED_NOTICE - 1
    assert repository.notice is None


def test_the_claim_is_read_once(monkeypatch):
    """Taken out of the environment, so a restart by hand an hour later
    does not inherit it."""
    monkeypatch.setenv(UPDATED_FROM, OLD)

    repository = make(FakeGit(status(head=NEW)), updated_from=None)

    assert repository._updated_from == OLD
    assert UPDATED_FROM not in os.environ


def test_a_restart_by_hand_says_nothing():
    repository = make(FakeGit(status()), updated_from=None)
    repository.loop()

    assert repository.notice is None


# --- the node ------------------------------------------------------------


def test_the_node_says_which_kind_of_machine_it_is_on():
    path = ("repository",)

    on = make(FakeGit(status()))._snapshot_if_opened(path)
    assert on["automatic updates"]["value"].startswith("on")

    off = make(FakeGit(status()), auto_update=False)._snapshot_if_opened(path)
    assert off["automatic updates"]["value"].startswith("off")
    assert machines.INSTALLATION in off["automatic updates"]["value"]


def test_the_node_says_what_is_running_and_what_the_update_is_doing():
    repository = make(FakeGit(status(behind=3)))
    repository.loop()

    states = repository._snapshot_if_opened(("repository",))

    assert states["running"]["value"] == OLD
    assert "restarting" in states["update"]["value"]
