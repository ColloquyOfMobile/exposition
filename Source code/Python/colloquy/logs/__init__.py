from colloquy.base import Base
from colloquy.logger import Logger
from colloquy.ui import leaves


class LogBranch(Base):
    """A thread path can have both its own log and logs from child threads."""

    def __init__(self, owner, branch):
        super().__init__(owner=owner)
        self._branch = branch
        self._nodes = {}

    @property
    def name(self):
        return self._branch.name

    @property
    def snapshot_children(self):
        if not self._branch.is_dir():
            return {}
        found = {}
        parent = self._branch.resolve()
        for entry in sorted(self._branch.iterdir()):
            if entry.resolve() != parent / entry.name:
                continue
            if entry.is_dir():
                name = entry.name
            elif entry.suffix == ".log" and entry.is_file():
                name = entry.stem
            else:
                continue
            found[name] = self._nodes.get(name) or LogBranch(self, self._branch / name)
        self._nodes = found
        return dict(found)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        log = self._branch.parent / (self.name + ".log")
        if log.is_file() and not log.is_symlink():
            try:
                content = log.read_text(encoding="utf-8", errors="replace")
            except OSError:
                content = "(log file unavailable)"
            states["content"] = leaves.pre(path, "content", content)
        return states


class Logs(LogBranch):
    """Browse the per-thread log files under local/logs/ from the web UI.
    The file list is rescanned on every request, so threads that start
    after the page was first opened still show up.
    """

    def __init__(self, owner):
        super().__init__(owner, Logger.folder())

    @property
    def name(self):
        return "logs"

    def _snapshot_if_opened(self, path):
        return Base._snapshot_if_opened(self, path)
