from pathlib import Path
from colloquy.base import Base


class LogFile(Base):
    """One thread's log file (local/logs/<thread name>.log, written by
    colloquy.logger.Logger). Open it in the web UI to read its current
    content - re-read from disk on every render, so it stays live."""

    def __init__(self, owner, file_path):
        super().__init__(owner=owner)
        self._file_path = file_path

    @property
    def name(self):
        return self._file_path.stem

    @property
    def snapshot_children(self):
        return {}

    def _snapshot_if_opened(self, path):
        try:
            content = self._file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            content = "(log file no longer exists)"

        return {
            "content": {
                "path": path + ("content",),
                "name": "content",
                "pre": content,
            }
        }


class Logs(Base):
    """Browse the per-thread log files under local/logs/ from the web UI.
    The file list is rescanned on every request, so threads that start
    after the page was first opened still show up.
    """

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._log_folder = Path("local/logs")
        self._files = {}

    @property
    def name(self):
        return "logs"

    @property
    def snapshot_children(self):
        if not self._log_folder.exists():
            return {}

        found = {}
        for file_path in sorted(self._log_folder.glob("*.log")):
            key = file_path.stem
            found[key] = self._files.get(key) or LogFile(
                owner=self, file_path=file_path
            )

        self._files = found
        return dict(self._files)
