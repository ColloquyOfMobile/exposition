from time import sleep, time
from pathlib import Path
from threading import Timer

class Logger:

    clean_thread = None
    _time_origin = time()
    _log_folder = Path("local/logs")

    if not _log_folder.is_dir():
        _log_folder.mkdir()

    for element in _log_folder.iterdir():
        lines = element.read_text().splitlines()
        lines = lines[-1000:]
        lines.extend(
            ("",
            "RESTART",
            "",)
        )
        text = "\n".join(lines[-1000:])
        element.write_text(text)

    def __init__(self, owner):
        self._owner = owner
        self._path = self._log_folder / f"{owner.name}.log"

    def __call__(self, msg):
        lines = msg.splitlines()
        if len(lines)>1:
            raise NotImplementedError
        msg = f"{round(time()-self._time_origin, 2)}: {msg=}"
        with self._path.open("a") as file:
            file.write(msg)
            file.write("\n")

    @classmethod
    def clean_folder(cls):
        print(f"Cleaning log folder...")
        for element in cls._log_folder.iterdir():
            lines = element.read_text().splitlines()
            lines = lines[-1000:]
            text = "\n".join(lines[-1000:])
            element.write_text(text)

        cls.clean_thread = Timer(60, cls.clean_folder)
        cls.clean_thread.start()