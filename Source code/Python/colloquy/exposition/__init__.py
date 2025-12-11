from time import time, sleep
import traceback
from colloquy.base import Base
from pathlib import Path
import traceback
from threading import Thread, Event, Lock
from .html import HTML
from utils import CustomDoc

class Exposition(Base):

    def __init__(self, owner):
        super().__init__(owner)
        self._html = HTML(owner=self)
        self._hardware = self.owner.hardware
        
        self._thread = None
        self._stop_event = Event()
        self._started_at = None        
        self._child_errors = []

        self[self.html.name] = self.html.handle_request
        self["start"] = self.start
        self["stop"] = self.stop

    def __call__(self, request):
        request = Path(request)
        if not request.parts:
            raise NotImplementedError

        key, *leftover = request.parts

        if key in self:
            self[key](request="/".join(leftover))
            return

        raise NotImplementedError(f"{key=}, {leftover=}, in {self=}")

    @property
    def is_started(self):
        if self._thread is None:
            return False
        return self._thread.is_alive()

    @property
    def child_errors(self):
        return self._child_errors

    @property
    def html(self):
        return self._html

    @property
    def name(self):
        return "exposition"

    @property
    def workspace(self):
        return self.colloquy.server.wsgi.root.body.workspace

    @property
    def hardware(self):
        return self._hardware

    @property
    def colloquy(self):
        return self.owner.colloquy

    def shutdown(self):
        self.stop()

    def start(self, request):
        self.child_errors.clear()
        self._started_at = time()
        self._stop_event.clear()
        self._thread = thread = Thread(target=self.run, name=self.path.as_posix())
        thread.start()

    def stop(self, request=None):
        self.hardware.shutdown()
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join()

    def run(self):
        try:
            self._run_unsafe()
        except Exception as error:
            raise NotImplementedError(self)

    def _run_unsafe(self):
        stop_event = self._stop_event.is_set
        with self.hardware.arduino:
            for bodies in self.hardware.bodies:
                bodies.drives.start(started_by=self)        
            
            while not stop_event():
                if self.child_errors:
                    self._stop_event.set()
                    self.hardware.shutdown()
                sleep(0.1)

    def add_error(self, origin, error):
        print(f"{origin=}")
        print(f"{error=}")
        
        self.child_errors.append(
            (origin, error)
        )
