from time import sleep, time
from pathlib import Path
from .logger import Logger
import traceback
from threading import Thread, Event, Lock
from server.html_element import HTMLElement

class ThreadElement(HTMLElement):

    _thread_pool = set()

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
        self._pool_lock = Lock()
        if self._owner is not None:
            self._owner.elements.add(self)

    def __repr__(self):
        return self.path.as_posix()

    def __eq__(self, other):
        if not isinstance(other, ThreadElement):
            return NotImplemented
        return self is other

    def __lt__(self, other):
        if not isinstance(other, ThreadElement):
            return NotImplemented
        return self.name < other.name

    def __hash__(self):
        return id(self)

    # 👇 Context manager methods
    def __enter__(self):
        self.stop_event.clear()
        # raise NotImplementedError(
        # f"for {self=}"
        # )

    def __exit__(self, exc_type, exc_value, traceback_obj):
        self.is_started = False
        self._thread_pool.discard(self.thread)
        if exc_type is not None:
            # self.stop()
            self.colloquy.stop()
            self._exception = exc_value
            msg = ''.join(traceback.format_exception(exc_type, exc_value, traceback_obj))
            self.log(msg)
            print(f"Error ({exc_type=}) in {self.path.as_posix()}")
        for element in self.elements:
            element.stop()
        for element in self.elements:
            element.join()
        self.log(f"Exited thread: {self.thread.name=}")
        return True  # suppress exception if any

    @property
    def is_started(self):
        for e in self.elements:
            if e.is_started:
                return True
        # raise NotImplementedError(f"Detect from here.")
        return self._is_started

    @is_started.setter
    def is_started(self, value):
        # if value:
            # self._is_started = value
            # self.owner.is_started = value
            # return
        self._is_started = value

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

    @property
    def thread_count(self):
        # for thread in self._thread_pool:
            # print(f"{thread=}, {thread.is_alive()=}")
        return len(self._thread_pool)

    def join(self):
        if self.thread is None:
            return
        for element in self.elements:
            element.join()
        self.thread.join()

    def _add_thread_to_pool(self, value):
        with self._pool_lock:
            self._thread_pool.add(value)

    def iter_thread_pool(self):
        yield from sorted(self._thread_pool, key=lambda x:x.name)

    def _sleep_min(self):
        sleep(0.01)

    def _setup(self, **kwargs):
        pass
        # raise NotImplementedError(f"for {self.name}, ({kwargs=})!")

    def start(self, **kwargs):
        self.stop_event.clear()

        self.log(f"Starting {self.path.as_posix()}...")
        self.is_started = True
        if self._thread is not None:
            if self._thread.is_alive():
                return
        self.threads.clear()
        self._thread = thread = Thread(target=self.run, name=self.path.as_posix())
        self.owner.threads.add(thread)
        self._add_thread_to_pool(thread)
        thread.start()
        self.log(f"...{self.path.as_posix()} started.")

    def stop(self, **kwargs):
        if self._is_started:
            self.stop_event.set()
            return
        for element in self.elements:
            element.stop()

    def run(self, **kwargs):
        with self:
            self._setup(**kwargs)
            while not self.stop_event.is_set():
                self._loop()
                self._sleep_min()

    def _loop(self):
        raise NotImplementedError(
            f"Called repeatedly until stopped! ({self=})"
            )