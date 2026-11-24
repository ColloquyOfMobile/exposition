# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/installation_sol2/shared.py

"""The record, kept on its own git branch and pushed from the laptop.

**Why a branch of its own, written with plumbing.** The record has to
reach every checkout, so it is committed and pushed. Committed to the
branch the code is on, it would cost the laptop a restart per press:
`Repository.needs_restart` (rightly) calls any new commit under a
running process new code, and the laptop restarts itself for that. It
would also leave the tree dirty between write and commit, and a progress
commit the laptop could not push would stop its automatic pull for good
(`--ff-only` cannot pass a local commit). So the record lives on
`installation-sol2-progress`, a branch holding one file, and is written
without a checkout: `hash-object` -> `mktree` -> `commit-tree` ->
`update-ref` -> `push`. The working tree, the index and the branch the
laptop runs never move.

**Only the laptop writes** (`machines.is_installation()`), because the
installation is where the work is done and one writer means a push is
only ever refused by an older copy of itself - which is merged
(`progress.merge`) and pushed again. Every other checkout reads
`origin/installation-sol2-progress`, which `Repository`'s routine fetch
brings in every five minutes, or `fetch the record` at once.

**Nothing here raises.** git that cannot run, a network that is down, a
branch that does not exist yet: each is a sentence on the page. A record
written while offline stays on the laptop's local branch and is pushed
by the next press or by `push the record now`.
"""
from datetime import datetime
from threading import Lock, Thread
from time import monotonic

from colloquy import machines
from colloquy.repository.git import FETCH_TIMEOUT, Git, GitError

from . import progress

BRANCH = "installation-sol2-progress"
LOCAL_REF = "refs/heads/" + BRANCH
REMOTE_REF = "refs/remotes/origin/" + BRANCH

# A render reads both refs at most this often: two or three local git
# calls, a few tens of milliseconds, while the command lock is held.
READ_EVERY = 5.0

# When this checkout has no identity of its own (a laptop that has only
# ever pulled), the record's commits are signed as the machine.
MACHINE_IDENTITY = ("-c", "user.name=Colloquy laptop", "-c", "user.email=colloquy-laptop@localhost")


def now():
    """The time a press is recorded at: local, to the second, sortable."""
    return datetime.now().isoformat(timespec="seconds")


class SharedRecord:
    """One record, read from both refs and written by the laptop."""

    def __init__(self, git=None, writer=None):
        self._git = git if git is not None else Git()
        self._writer = machines.is_installation() if writer is None else bool(writer)
        self._lock = Lock()
        self._pending = None       # (record, summary) waiting for the worker
        self._worker = None
        self._report = None        # the last push or fetch, in words
        self._cached = None        # (record, ahead) as last read
        self._read_at = None

    @property
    def is_writer(self):
        return self._writer

    @property
    def report(self):
        return self._report

    # --- reading --------------------------------------------------------

    def _tip(self, ref):
        try:
            return self._git.run("rev-parse", "--verify", "--quiet", ref + "^{commit}")
        except GitError:
            return None

    def _show(self, tip):
        if tip is None:
            return {}
        try:
            return progress.parse(self._git.run("show", f"{tip}:{progress.FILE_NAME}"))
        except GitError:
            return {}

    def _ahead(self, local, remote):
        """How many of the laptop's record commits origin has not got."""
        if local is None or local == remote:
            return 0
        if remote is None:
            spec = local
        else:
            spec = f"{remote}..{local}"
        try:
            return int(self._git.run("rev-list", "--count", spec))
        except (GitError, ValueError):
            return 0

    def read(self):
        """The record as this checkout knows it, with anything still
        waiting to be written on top. Cached for `READ_EVERY` seconds."""
        if self._read_at is None or monotonic() - self._read_at > READ_EVERY:
            local, remote = self._tip(LOCAL_REF), self._tip(REMOTE_REF)
            record = progress.merge(self._show(remote), self._show(local))
            self._cached = (record, self._ahead(local, remote), remote is not None)
            self._read_at = monotonic()
        record, _, _ = self._cached
        pending = self._pending
        return progress.merge(record, pending[0]) if pending else record

    def where(self):
        """One line for the page: where the record shown comes from."""
        self.read()
        _, ahead, on_origin = self._cached
        if self._pending is not None:
            state = "writing the last press - refresh in a moment"
        elif ahead:
            state = (
                f"{ahead} record commit{'s' if ahead != 1 else ''} on this "
                "laptop not pushed yet - press 'push the record now'"
            )
        elif on_origin:
            state = f"as on origin/{BRANCH}"
        else:
            state = f"nothing on origin/{BRANCH} yet"
        who = (
            "this is the laptop, which writes it"
            if self._writer
            else "read only here: the Colloquy laptop writes it"
        )
        return f"{state}; {who}"

    def _forget(self):
        self._read_at = None

    # --- writing (the laptop) -------------------------------------------

    def write(self, record, summary):
        """Hand a new record to the worker; returns at once. Presses that
        arrive while it is pushing are merged and go out together."""
        if not self._writer:
            return "refused: only the Colloquy laptop writes the record"
        with self._lock:
            if self._pending is None:
                self._pending = (record, summary)
            else:
                old, old_summary = self._pending
                self._pending = (progress.merge(old, record), f"{old_summary}; {summary}")
            if self._worker is None or not self._worker.is_alive():
                self._worker = Thread(target=self._work, name="installation sol2 record", daemon=True)
                self._worker.start()
        return None

    def push_now(self):
        """Push whatever the local branch has that origin has not."""
        if not self._writer:
            return "refused: only the Colloquy laptop writes the record"
        return self.write({}, "pushing what was not pushed")

    def _work(self):
        while True:
            with self._lock:
                job = self._pending
                if job is None:
                    return
            record, summary = job
            self._report = self.publish(record, summary)
            with self._lock:
                if self._pending is job:
                    self._pending = None
            self._forget()

    def _identity(self):
        try:
            if self._git.run("config", "user.email"):
                return ()
        except GitError:
            pass
        return MACHINE_IDENTITY

    def publish(self, record, summary, retry=True):
        """Commit `record` (merged with both refs) and push it. Returns the
        sentence for the page. Synchronous: the worker's half."""
        try:
            local, remote = self._tip(LOCAL_REF), self._tip(REMOTE_REF)
            merged = progress.merge(self._show(remote), self._show(local), record)
            parent = self._parent(local, remote)
            commit = self._commit(merged, parent, summary)
            if commit != local:
                self._git.run("update-ref", LOCAL_REF, commit)
            if commit == remote:
                return f"nothing new to push - origin/{BRANCH} has it"
        except GitError as error:
            return f"not recorded: {error}"
        try:
            self._git.run(
                "push", "--quiet", "origin", f"{LOCAL_REF}:refs/heads/{BRANCH}",
                timeout=FETCH_TIMEOUT,
            )
        except GitError as error:
            text = str(error)
            if retry and ("rejected" in text or "fetch first" in text or "non-fast-forward" in text):
                try:
                    self._git.run("fetch", "--quiet", "origin", BRANCH, timeout=FETCH_TIMEOUT)
                except GitError as fetch_error:
                    return f"recorded on this laptop, not pushed: {fetch_error}"
                return self.publish(record, summary, retry=False)
            return f"recorded on this laptop, not pushed: {text}"
        return f"recorded and pushed at {now()[11:]}: {summary}"

    def _parent(self, local, remote):
        """What the next record commit follows: the laptop's own branch
        when origin's is behind it, otherwise origin's (the merge has
        already taken in whatever a divergent local branch said)."""
        if local is None:
            return remote
        if remote is None or local == remote:
            return local
        try:
            self._git.run("merge-base", "--is-ancestor", remote, local)
            return local
        except GitError:
            return remote

    def _commit(self, record, parent, summary):
        """The commit holding `record`, or `parent` itself when its tree
        already says exactly that."""
        blob = self._git.run("hash-object", "-w", "--stdin", input=progress.dump(record))
        tree = self._git.run("mktree", input=f"100644 blob {blob}\t{progress.FILE_NAME}\n")
        if parent is not None and self._git.run("rev-parse", parent + "^{tree}") == tree:
            return parent
        message = f"Installation sol2: {summary}"
        args = (*self._identity(), "commit-tree", tree, "-m", message)
        if parent is not None:
            args += ("-p", parent)
        return self._git.run(*args)

    # --- fetching (everywhere else) -------------------------------------

    def fetch(self):
        """Bring origin's record in now, off the request thread."""
        def work():
            try:
                self._git.run("fetch", "--quiet", "origin", BRANCH, timeout=FETCH_TIMEOUT)
                self._report = f"fetched at {now()[11:]}"
            except GitError as error:
                self._report = f"fetch failed: {error}"
            self._forget()

        Thread(target=work, name="installation sol2 fetch", daemon=True).start()
        return "fetching - refresh in a moment"
