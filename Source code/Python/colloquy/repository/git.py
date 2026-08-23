# -*- coding: utf-8 -*-
# Source code/Python/colloquy/repository/git.py

"""The handful of git commands the page needs, and nothing else.

The repo is worked on from two computers, and the way work gets lost is
that one of them sits for a week on a tree the other has moved past. The
page already knows everything else about the state of the installation;
this is so it also knows that, without anybody remembering to open a
terminal and type `git fetch`.

Two rules shape all of it:

- **Only `fetch` runs by itself.** Fetching writes nothing but
  `.git/refs/remotes` - it cannot touch a file in the working tree, so it
  is safe to do every few minutes behind somebody's back. Merging is not,
  so `pull` is a link somebody clicks, and it is `--ff-only`: it either
  winds the branch forward or refuses, and there is no third outcome
  where it leaves a half-merged tree in the gallery.
- **Nothing here raises out of a loop.** A laptop in an exhibition space
  is off the network as often as not, and a fetch that cannot reach
  GitHub is an ordinary Tuesday, not a fault in the installation. Every
  failure comes back as a `GitError` for the caller to show as a reading,
  and `Repository` turns none of them into thread errors.

The environment matters more than it looks: git blocks *forever* on a
credential prompt nobody is at the keyboard to answer, which on a
headless machine is indistinguishable from a hang. `GIT_TERMINAL_PROMPT`
and the two askpass variables make it fail in a second instead, saying
that authentication is what failed.
"""
import os
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

# .../exposition/Source code/Python/colloquy/repository/git.py
#      [4]         [3]         [2]     [1]      [0]
REPO_FOLDER = Path(__file__).resolve().parents[4]

FETCH_TIMEOUT = 60
COMMAND_TIMEOUT = 15

# Don't flash a console window every few minutes if this is ever run
# under pythonw. No-op anywhere but Windows.
_NO_WINDOW = {}
if sys.platform == "win32":
    _NO_WINDOW["creationflags"] = subprocess.CREATE_NO_WINDOW


class GitError(Exception):
    """git could not answer - not installed, not a repo, no network, no
    credentials. Something to show on the page, never something to stop a
    thread over."""


class Status(namedtuple("Status", "branch upstream behind ahead dirty newest")):
    """Where this checkout stands against origin, as of the last fetch.

    `behind` is how many commits origin has that we do not - the whole
    point of the exercise. `ahead` is the mirror of it, and worth showing
    beside it: being 2 ahead and 3 behind is the case where a plain pull
    would merge, which is exactly the case this refuses to do quietly.
    `dirty` counts the lines of `git status --porcelain`, so it counts
    files touched, staged or not.
    """

    @property
    def is_behind(self):
        return self.behind > 0

    @property
    def can_fast_forward(self):
        """Would `pull --ff-only` do anything, and would it succeed?"""
        return self.behind > 0 and self.ahead == 0


def environment():
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    # An unset GIT_ASKPASS falls back to SSH_ASKPASS and then to whatever
    # helper is configured, which on Windows is a GUI dialog nobody in a
    # gallery is going to see, let alone dismiss.
    env["GIT_ASKPASS"] = ""
    env["SSH_ASKPASS"] = ""
    return env


class Git:
    """git in one folder. Holds no state - every method shells out."""

    def __init__(self, folder=REPO_FOLDER):
        self._folder = Path(folder)

    def __repr__(self):
        return f"Git({self._folder.as_posix()})"

    @property
    def folder(self):
        return self._folder

    def run(self, *args, timeout=COMMAND_TIMEOUT):
        """One git command, its stdout stripped. Raises GitError for every
        way it can fail, so no caller has to know about subprocess."""
        try:
            completed = subprocess.run(
                ("git",) + args,
                cwd=self._folder,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=environment(),
                **_NO_WINDOW,
            )
        except FileNotFoundError as error:
            raise GitError(
                "git is not installed, or not on this machine's PATH"
            ) from error
        except subprocess.TimeoutExpired as error:
            spelled = " ".join(args)
            raise GitError(f"`git {spelled}` gave no answer within {timeout}s") from error
        except OSError as error:
            raise GitError(f"could not run git: {error}") from error

        if completed.returncode != 0:
            raise GitError(explain(args, completed))

        return completed.stdout.strip()

    # --- the questions -------------------------------------------------

    def branch(self):
        """The branch checked out, or None when the head is detached."""
        name = self.run("rev-parse", "--abbrev-ref", "HEAD")
        if name == "HEAD":
            return None
        return name

    def upstream(self, branch):
        """What this branch is tracked against on origin.

        `@{upstream}` is the honest answer and the one git itself uses,
        but a branch that has never been pushed has none. A local
        `Refactor` sitting beside an `origin/Refactor` it was never told
        about is still a branch somebody wants told about new commits, so
        fall back to the remote branch of the same name before giving up.
        """
        try:
            return self.run(
                "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"
            )
        except GitError:
            pass

        candidate = f"origin/{branch}"
        try:
            self.run("rev-parse", "--verify", "--quiet", candidate + "^{commit}")
        except GitError:
            raise GitError(f"{branch} is not tracking anything on origin")
        return candidate

    def counts(self, upstream):
        """(behind, ahead) - commits on origin we lack, and ours it lacks."""
        counted = self.run("rev-list", "--left-right", "--count", f"{upstream}...HEAD")
        behind, ahead = counted.split()
        return int(behind), int(ahead)

    def dirty(self):
        """How many files in the working tree are modified or untracked."""
        porcelain = self.run("status", "--porcelain")
        if not porcelain:
            return 0
        return len(porcelain.splitlines())

    def newest(self, upstream):
        """Origin's newest commit, as the page would like to read it."""
        return self.run("log", "-1", "--format=%h %s", upstream)

    # --- the two things it does ----------------------------------------

    def fetch(self):
        """Ask origin what it has. Writes nothing outside .git/."""
        self.run("fetch", "--quiet", timeout=FETCH_TIMEOUT)

    def status(self):
        """Everything the page shows, in one go, without fetching."""
        branch = self.branch()
        if branch is None:
            raise GitError("this checkout is on a detached head, not a branch")
        upstream = self.upstream(branch)
        behind, ahead = self.counts(upstream)
        return Status(
            branch=branch,
            upstream=upstream,
            behind=behind,
            ahead=ahead,
            dirty=self.dirty(),
            newest=self.newest(upstream),
        )

    def pull(self):
        """Wind the branch forward, or refuse. Never merges."""
        return self.run("pull", "--ff-only", timeout=FETCH_TIMEOUT)


def explain(args, completed):
    """What to put on the page when git said no.

    git writes its reasons to stderr and its answers to stdout, but
    `rev-parse --verify --quiet` says nothing at all, so fall back to
    naming the command rather than showing an empty error.
    """
    for stream in (completed.stderr, completed.stdout):
        text = (stream or "").strip()
        if text:
            return text.splitlines()[0]
    return f"`git {' '.join(args)}` failed ({completed.returncode})"
