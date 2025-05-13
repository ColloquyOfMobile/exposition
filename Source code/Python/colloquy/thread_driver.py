from time import sleep, time
from pathlib import Path
from .logger import Logger
import traceback
from threading import Thread, Event
from server.html_element import HTMLElement

class ThreadDriver(HTMLElement):

    def __init__(self, name, owner):
        HTMLElement.__init__(self, owner)
        self._owner = owner
        self._name = name
        self._path = Path(name)
        self._is_started = False

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

    def __eq__(self, other):
        if not isinstance(other, ThreadDriver):
            return NotImplemented
        return self is other

    def __lt__(self, other):
        if not isinstance(other, ThreadDriver):
            return NotImplemented
        return self.name < other.name

    def __hash__(self):
        return id(self)

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
            print(f"Error ({exc_type=}) in {self.name}")
        self.stop()
        return True  # suppress exception if any

    @property
    def param(self):
        return self.owner.params

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

    def _setup(self, **kwargs):
        raise NotImplementedError(f"for {self.name}, ({kwargs=})!")

    def start(self, **kwargs):
        if kwargs:
            self._setup(**kwargs)

        self.log(f"Starting {self.path.as_posix()}...")
        self._is_started = True
        if self._thread is not None:
            assert not self._thread.is_alive()
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
        self._is_started = False

    def run(self, **kwargs):
        with self:
            while not self.stop_event.is_set():
                self._loop()
                self._sleep_min()

    def _loop(self):
        raise NotImplementedError(
            f"Called repeatedly until stopped! ({self=})"
            )