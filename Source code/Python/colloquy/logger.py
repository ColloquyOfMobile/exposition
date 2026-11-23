from time import time
import threading
from pathlib import Path
import shutil
from threading import Lock


class Logger:
    _time_origin = time()
    _log_folder = Path("local/logs")
    _write_lock = Lock()

    @classmethod
    def start_session(cls, *, preview=False):
        """Only the process starting a server owns its log directory."""
        cls._log_folder = Path("local/mock logs" if preview else "local/logs")
        if cls._log_folder.exists():
            shutil.rmtree(cls._log_folder)
        cls._log_folder.mkdir(parents=True)

    @classmethod
    def folder(cls):
        return cls._log_folder

    def __call__(self, msg: str):

        current = threading.current_thread()
        main_thread = threading.main_thread()
        msg = self._format(msg=msg)

        if current == main_thread:
            print(msg)

        self._write(msg)

    def _write(self, msg: str):
        """Write log to current thread's file, creating directories if needed."""

        thread_name = threading.current_thread().name
        file_path = (self._log_folder / thread_name).with_suffix(".log")

        # Keep the session history on disk. Only the live reader needs a
        # bounded window; rewriting an active file can tear a log record.
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with self._write_lock:
            with file_path.open("a", encoding="utf-8") as stream:
                stream.write(msg + "\n")

    def _format(self, msg):
        time_header = self._format_time()  # f"{round(time()-self._time_origin, 2)}:"
        lines = msg.splitlines()
        if len(lines) == 1:
            return f"{time_header} {msg}"

        new_lines = [f"{time_header}:"]
        for line in lines:
            new_lines.append(f"+ {line}")

        return "\n".join(new_lines)

    def _format_time(self):
        elapsed = time() - self._time_origin
        h = int(elapsed // 3600)
        m = int((elapsed % 3600) // 60)
        s = elapsed % 60

        if h:
            return f"{h:02d}:{m:02d}:{s:05.2f}"
        elif m:
            return f"{m:02d}:{s:05.2f}"
        else:
            return f"{s:05.2f}s"
