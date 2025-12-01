from time import sleep, time
from pathlib import Path
from threading import Timer
from colloquy.base import Base 
from datetime import datetime

class Logger(Base):

    _instances = {}
    _time_origin = time()
    _log_folder = Path("local/logs")

    if not _log_folder.is_dir():
        _log_folder.mkdir()      

    def __init__(self, owner):
        raise NotImplementedError(f"Fix logger.")
        super().__init__(owner)
        self._line_count = None    
        self._folder = self._log_folder / self.owner.name
        self._path = self._folder.parent / f"{owner.name}.log"

        assert self._path not in self._instances, f"{self._path=}"
        self._instances[self._path] = self  

    def _init(self):
        self._init_file()
            
        lines = self._path.read_text().splitlines()

        self._line_count = len(lines)
        lines.extend(
            ("",
            f"RESTART {datetime.now()}",
            "",)
        )
        text = "\n".join(lines[-500:])
        self._path.write_text(text) 

    def _init_file(self):
        if not self._path.exists():
            self._path.touch()

    def mkdir(self):
        self._folder.mkdir()

    @property
    def folder(self):
        return self._folder

    @property
    def name(self):
        return "logger"

    def mkdir(self):
        self._folder.mkdir()

    def __call__(self, msg):
        if self._line_count is None:
            self._init()
        msg_lines = self._format(msg)
        msg_line_count = len(msg_lines)
        line_count = self._line_count + msg_line_count

        if line_count > 1000:
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