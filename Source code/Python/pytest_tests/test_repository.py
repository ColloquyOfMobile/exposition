"""The git-origin watch: what it says, and what it refuses to do.

Nothing here runs git. `Git` is replaced by a double that answers from a
dict, and the two tests that do exercise the real class replace
`subprocess.run` instead - the point of those is the mapping from how a
subprocess failed to what the page says, which is the part that is easy
to get wrong and impossible to see from a green network.

The one real filesystem fact checked is REPO_FOLDER: it is index
arithmetic over `__file__`, so it goes wrong silently the day the module
moves a directory, and it goes wrong by fetching in whatever folder the
process happens to be in.
"""
import subprocess
from types import SimpleNamespace

import pytest

from colloquy.repository import Repository
from colloquy.repository.git import (
    REPO_FOLDER,
    Git,
    GitError,
    Status,
    environment,
    explain,
)


def status(behind=0, ahead=0, dirty=0, branch="Refactor", upstream="origin/Refactor"):
    return Status(
        branch=branch,
        upstream=upstream,
        behind=behind,
        ahead=ahead,
        dirty=dirty,
        newest="abc1234 a commit",
    )


class FakeGit:
    """Answers the six questions `Repository` asks, and records the two
    things it can be told to do."""

    def __init__(self, status=None, error=None, pull_answer="Fast-forward"):
        self._status = status
        self._error = error
        self._pull_answer = pull_answer
        self.fetched = 0
        self.pulled = 0

    def fetch(self):
        self.fetched += 1
        if self._error is not None:
            raise GitError(self._error)

    def status(self):
        if self._error is not None:
            raise GitError(self._error)
        return self._status

    def pull(self):
        self.pulled += 1
        if self._error is not None:
            raise GitError(self._error)
        return self._pull_answer


def make_repository(git):
    owner = SimpleNamespace(owners=[], path=REPO_FOLDER, name="colloquy")
    return Repository(owner=owner, git=git)


# --- Status ---------------------------------------------------------------


@pytest.mark.parametrize(
    "behind, ahead, is_behind, can_ff",
    [
        (0, 0, False, False),
        (3, 0, True, True),
        (0, 2, False, False),
        # The case the whole --ff-only rule exists for: both sides have
        # moved, so winding forward is not on the table and a plain pull
        # would quietly merge.
        (3, 2, True, False),
    ],
)
def test_status_reads_the_two_counts(behind, ahead, is_behind, can_ff):
    reading = status(behind=behind, ahead=ahead)
    assert reading.is_behind is is_behind
    assert reading.can_fast_forward is can_ff


# --- the summary line -----------------------------------------------------


def test_summary_before_any_check():
    assert make_repository(FakeGit()).summary == "not checked yet"


def test_summary_when_origin_is_ahead():
    repository = make_repository(FakeGit(status=status(behind=3)))
    repository.check()
    assert repository.summary == "3 commits to pull from origin/Refactor"


def test_summary_counts_one_commit_singly():
    repository = make_repository(FakeGit(status=status(behind=1)))
    repository.check()
    assert repository.summary == "1 commit to pull from origin/Refactor"


def test_summary_when_up_to_date():
    repository = make_repository(FakeGit(status=status()))
    repository.check()
    assert repository.summary == "up to date with origin/Refactor"


def test_summary_when_only_we_are_ahead():
    repository = make_repository(FakeGit(status=status(ahead=2)))
    repository.check()
    assert repository.summary == "2 commits to push to origin/Refactor"


def test_summary_when_both_have_moved():
    repository = make_repository(FakeGit(status=status(behind=3, ahead=2)))
    repository.check()
    assert repository.summary == (
        "3 commits on origin/Refactor, 2 commits here it has not got"
    )


# --- a check that fails ---------------------------------------------------


def test_a_failed_check_reports_rather_than_raising():
    repository = make_repository(FakeGit(error="could not resolve host: github.com"))
    repository.check()
    assert repository.error == "could not resolve host: github.com"
    assert repository.summary == (
        "could not check: could not resolve host: github.com"
    )


def test_a_failed_check_keeps_the_last_thing_it_knew():
    """Being 3 behind as of ten minutes ago beats knowing nothing at all -
    a laptop in a gallery loses its network all the time."""
    git = FakeGit(status=status(behind=3))
    repository = make_repository(git)
    repository.check()

    git._error = "could not resolve host: github.com"
    repository.check()

    assert repository.status.behind == 3
    assert repository.error is not None


def test_a_check_that_succeeds_again_clears_the_error():
    git = FakeGit(error="could not resolve host: github.com")
    repository = make_repository(git)
    repository.check()
    assert repository.error is not None

    git._error = None
    git._status = status()
    repository.check()
    assert repository.error is None


# --- pull, and its four refusals -----------------------------------------


def test_pull_refuses_before_anything_has_been_checked():
    git = FakeGit()
    repository = make_repository(git)
    assert "check now first" in repository.pull()
    assert git.pulled == 0


def test_pull_refuses_over_uncommitted_work():
    """The exact accident this whole node exists to prevent: the other
    computer's unpushed edits sitting in the working tree."""
    git = FakeGit(status=status(behind=3, dirty=2))
    repository = make_repository(git)
    repository.check()

    report = repository.pull()
    assert "2 files changed here and not committed" in report
    assert git.pulled == 0


def test_pull_refuses_when_there_is_nothing_to_pull():
    git = FakeGit(status=status())
    repository = make_repository(git)
    repository.check()

    assert "nothing to pull" in repository.pull()
    assert git.pulled == 0


def test_pull_refuses_to_merge():
    git = FakeGit(status=status(behind=3, ahead=2))
    repository = make_repository(git)
    repository.check()

    report = repository.pull()
    assert "wants doing by hand" in report
    assert git.pulled == 0


def test_pull_fast_forwards_and_asks_for_a_restart():
    git = FakeGit(status=status(behind=3))
    repository = make_repository(git)
    repository.check()

    repository.pull()
    assert git.pulled == 1
    # Python read the modules at startup; the pulled code is on disk and
    # not running until somebody restarts.
    assert repository.needs_restart is True


class StartedRepository(Repository):
    """A repository whose watch is running, without running one.

    conftest forbids .start() in this suite, and the branch under test is
    the one that asks "is there a loop to hand this to?".
    """

    @property
    def is_started(self):
        return True


def test_pull_hands_the_network_half_to_the_loop():
    """A pull is a network round trip that can sit on a dead connection
    for a minute, and Colloquy.get_states holds one lock for the whole
    application - so a minute inside a request is a minute in which no
    page in the tree answers. It must not happen there."""
    git = FakeGit(status=status(behind=3))
    owner = SimpleNamespace(owners=[], path=REPO_FOLDER, name="colloquy")
    repository = StartedRepository(owner=owner, git=git)
    repository.check()

    report = repository.pull()
    assert "refresh in a moment" in report
    assert git.pulled == 0

    # ...and the loop is what actually does it.
    repository.loop()
    assert git.pulled == 1
    assert repository.needs_restart is True


def test_a_refusal_still_answers_immediately():
    """Only the network half is handed off. The refusals read the last
    status and touch nothing, so they stay instant - the reader gets told
    straight away why nothing is going to happen."""
    git = FakeGit(status=status(behind=3, dirty=2))
    owner = SimpleNamespace(owners=[], path=REPO_FOLDER, name="colloquy")
    repository = StartedRepository(owner=owner, git=git)
    repository.check()

    assert "not committed" in repository.pull()
    # Nothing was queued for the loop either.
    repository.loop()
    assert git.pulled == 0


def test_a_handed_off_pull_re_checks_before_it_runs():
    """Asked for on one thread and done on another, so the answer can
    change in between - the tree can be edited while the click is in the
    air. Pulling over somebody's uncommitted work is the one outcome this
    whole node exists to prevent."""
    git = FakeGit(status=status(behind=3))
    owner = SimpleNamespace(owners=[], path=REPO_FOLDER, name="colloquy")
    repository = StartedRepository(owner=owner, git=git)
    repository.check()
    repository.pull()

    # Somebody starts editing before the loop gets to it.
    git._status = status(behind=3, dirty=1)
    repository.check()
    repository.loop()

    assert git.pulled == 0
    assert "not committed" in repository._pull_report


def test_a_failed_pull_is_reported_not_raised():
    git = FakeGit(status=status(behind=3))
    repository = make_repository(git)
    repository.check()

    git._error = "unable to access github.com"
    report = repository.pull()
    assert report.startswith("pull failed:")
    assert repository.needs_restart is False


# --- what the page is offered --------------------------------------------


def test_pull_is_offered_only_when_origin_has_something():
    git = FakeGit(status=status())
    repository = make_repository(git)
    repository.check()
    assert "pull" not in repository.snapshot_children
    assert "check now" in repository.snapshot_children

    git._status = status(behind=1)
    repository.check()
    assert "pull" in repository.snapshot_children


def test_the_node_draws_its_readings():
    repository = make_repository(FakeGit(status=status(behind=3)))
    repository.check()
    states = repository._snapshot_if_opened(("repository",))

    assert states["summary"]["value"] == "3 commits to pull from origin/Refactor"
    assert states["behind"]["value"] == "3"
    assert states["ahead"]["value"] == "0"
    assert states["working tree"]["value"] == "clean"
    assert states["branch"]["value"] == "Refactor -> origin/Refactor"
    assert "ago" in states["last checked"]["value"]


def test_last_checked_says_never_before_a_check():
    repository = make_repository(FakeGit())
    states = repository._snapshot_if_opened(("repository",))
    assert states["last checked"]["value"] == "never"


def test_check_now_runs_inline_when_nothing_is_watching():
    """No thread to hand the job to, so it does it itself - somebody who
    clicked it is willing to wait for it."""
    git = FakeGit(status=status())
    repository = make_repository(git)
    repository.check_now()
    assert git.fetched == 1


# --- the Git wrapper's own failure mapping --------------------------------


def test_missing_git_is_a_git_error(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", missing)
    with pytest.raises(GitError, match="not installed"):
        Git().run("status")


def test_a_hung_fetch_is_a_git_error(monkeypatch):
    """The case the timeouts exist for: git waiting on a network, or on a
    credential prompt nobody is at the keyboard to answer."""

    def hangs(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="git fetch", timeout=60)

    monkeypatch.setattr(subprocess, "run", hangs)
    with pytest.raises(GitError, match="gave no answer"):
        Git().fetch()


def test_a_nonzero_exit_reports_gits_own_first_line(monkeypatch):
    def refuses(*args, **kwargs):
        return SimpleNamespace(
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository\nsecond line\n",
        )

    monkeypatch.setattr(subprocess, "run", refuses)
    with pytest.raises(GitError, match="fatal: not a git repository"):
        Git().run("status")


def test_explain_falls_back_through_stderr_stdout_then_the_command():
    on_stderr = SimpleNamespace(returncode=1, stdout="out", stderr=" boom \n")
    assert explain(("status",), on_stderr) == "boom"

    on_stdout = SimpleNamespace(returncode=1, stdout="said this", stderr="")
    assert explain(("status",), on_stdout) == "said this"

    # `rev-parse --verify --quiet` says nothing at all when it fails.
    silent = SimpleNamespace(returncode=1, stdout="", stderr="")
    assert explain(("rev-parse", "--verify"), silent) == (
        "`git rev-parse --verify` failed (1)"
    )


def test_git_never_waits_on_a_credential_prompt():
    env = environment()
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert env["GIT_ASKPASS"] == ""
    assert env["SSH_ASKPASS"] == ""


# --- upstream, and its fallback -------------------------------------------


class RunRecorder:
    """Stands in for Git.run: answers by command, raises for the rest."""

    def __init__(self, answers):
        self._answers = answers
        self.calls = []

    def __call__(self, *args, timeout=None):
        self.calls.append(args)
        if args in self._answers:
            return self._answers[args]
        raise GitError("no")


def test_upstream_prefers_what_the_branch_tracks():
    run = RunRecorder(
        {
            ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"): (
                "origin/Refactor"
            )
        }
    )
    git = Git()
    git.run = run
    assert git.upstream("Refactor") == "origin/Refactor"


def test_upstream_falls_back_to_the_remote_branch_of_the_same_name():
    """A branch that was never pushed with -u tracks nothing, but an
    origin/<name> beside it is still what somebody wants told about."""
    run = RunRecorder({("rev-parse", "--verify", "--quiet", "origin/Refactor^{commit}"): ""})
    git = Git()
    git.run = run
    assert git.upstream("Refactor") == "origin/Refactor"


def test_upstream_gives_up_when_origin_has_no_such_branch():
    git = Git()
    git.run = RunRecorder({})
    with pytest.raises(GitError, match="not tracking anything"):
        git.upstream("a-local-experiment")


def test_counts_reads_behind_then_ahead():
    git = Git()
    git.run = RunRecorder(
        {("rev-list", "--left-right", "--count", "origin/Refactor...HEAD"): "3\t2"}
    )
    assert git.counts("origin/Refactor") == (3, 2)


def test_a_detached_head_is_reported_not_guessed_at():
    git = Git()
    git.run = RunRecorder({("rev-parse", "--abbrev-ref", "HEAD"): "HEAD"})
    with pytest.raises(GitError, match="detached head"):
        git.status()


# --- the one filesystem fact ----------------------------------------------


def test_repo_folder_is_the_checkout_this_file_is_in():
    assert (REPO_FOLDER / "main.py").is_file()
    assert (REPO_FOLDER / ".git").exists()
