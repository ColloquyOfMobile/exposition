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
        self._stop_event = Event()
        self._stop_event.set()
        self._elements = set()
        if self._owner is not None:
            self._owner.elements.add(self)

    # 👇 Context manager methods
    def __enter__(self):
        raise NotImplementedError(
        "Set up before starting a thread."
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

    def sleep_min(self):
        sleep(0.01)

    def start(self):
        assert self._thread is None
        self.stop_event.clear()
        self._thread = thread = Thread(target=self.run, name=self._name)
        thread.start()

    def stop(self):
        for element in self.elements:
            element.stop()

        if self._stop_event.is_set():
            return
        self.stop_event.set()
        self._thread.join()
        self._thread = None

    def run(self, **kwargs):
        print(f"Running {self.name}...")
        print(f"{self=}...")

        with self:
            while not self.stop_event.is_set():
                self._loop()
        # try:
            # self._run_setup()
            # self._run_loop()
            # self._run_setdown()
        # except Exception:
            # msg = traceback.format_exc()
            # self.log(msg)
            # self.colloquy.stop_event.set()
            # self._run_setdown()
            # self._thread = None
            # raise

    def _loop(self):
        raise NotImplementedError(
            "Called repeatedly until stopped!"
            )