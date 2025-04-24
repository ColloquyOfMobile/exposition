from time import sleep, time
from pathlib import Path
from .logger import Logger
import traceback
from threading import Thread, Event

class ThreadDriver:

    def __init__(self, name, owner):
        self._owner = owner
        self._name = name
        self._path = Path(name)
        if owner is not None:
            self._path = owner.path / name
        self._log = Logger(owner=self)
        self._thread = None
        self._threads = set()
        self._stop_event = Event()
        self._stop_event.set()
        self._elements = set()
        if self._owner is not None:
            self._owner.elements.add(self)

    # 👇 Context manager methods
    def __enter__(self):
        raise NotImplementedError(
        f"for {self=}"
        )

    def __exit__(self, exc_type, exc_value, traceback_obj):
        if exc_type is not None:
            self.colloquy.stop_event.set()
            self._exception = exc_value
            msg = ''.join(traceback.format_exception(exc_type, exc_value, traceback_obj))
            self.log(msg)
        self.stop()
        # self._thread = None
        return False  # re-raise exception if any

    @property
    def thread(self):
        return self._thread

    @property
    def threads(self):
        return self._threads

    @property
    def owner(self):
        return self._owner

    @property
    def path(self):
        return self._path

    @property
    def colloquy(self):
        return self._owner.colloquy

    @property
    def elements(self):
        return self._elements

    @property
    def stop_event(self):
        return self._stop_event

    @property
    def name(self):
        return self._name

    @property
    def log(self):
        return self._log

    def _sleep_min(self):
        sleep(0.01)

    def start(self):
        self.log(f"Starting {self.path.as_posix()}...")
        if self._thread is not None:
            assert not self._thread.is_alive() is None
        self.stop_event.clear()
        self._thread = thread = Thread(target=self.run, name=self._name)
        self.owner.threads.add(thread)
        thread.start()
        self.log(f"...{self.path.as_posix()} started.")

    def stop(self):
        self.stop_event.set()
        for element in self.elements:
            element.stop()

        for thread in self.threads:
            thread.join()

    def run(self, **kwargs):
        print(f"Running {self.path}...")

        with self:
            while not self.stop_event.is_set():
                self._loop()
                self._sleep_min()

        print(f"Stopped {self.path}!")

    def _loop(self):
        raise NotImplementedError(
            f"Called repeatedly until stopped! ({self=})"
            )