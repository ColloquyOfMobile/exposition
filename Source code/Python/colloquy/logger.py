from time import sleep, time
from pathlib import Path
from threading import Timer
from datetime import datetime

class Logger:
    
    _instances = {}
    clean_thread = None
    _started = False
    _time_origin = time()
    _log_folder = Path("local/logs")

    if not _log_folder.is_dir():
        _log_folder.mkdir()

    def __init__(self, owner):
        self._owner = owner
        self._path = self._log_folder / f"{owner.name}.log"
        assert self._path not in self._instances
        self._instances[self._path] = self
        if not self._path.exists():
            self._path.touch()
        self._line_count = len(self._path.read_text().splitlines())
        lines = self._path.read_text().splitlines()
        lines.extend(
            ("",
            f"RESTART {datetime.now()}",
            "",)
        )
        text = "\n".join(lines[-500:])
        self._path.write_text(text)

    def __call__(self, msg):
        msg_lines = self._format(msg)
        msg_line_count = len(msg_lines)
        line_count = self._line_count + msg_line_count

        if line_count > 1000:
            print(f"Cleaning {self._path.as_posix()}")
            lines = self._path.read_text().splitlines()
            lines.extend(msg_lines)
            self._path.write_text("\n".join(lines[-500:]))
            return

        with self._path.open("a") as file:
            file.write("\n".join(msg_lines))
            file.write("\n")

    def _format(self, msg):
        time_header = f"{round(time()-self._time_origin, 2)}:"
        lines = msg.splitlines()
        if len(lines) == 1:
            return [f"{time_header} {msg}"]

        new_lines = [f"{time_header}"]
        for line in lines:
            new_lines.append(f"| {line}")

        return new_lines