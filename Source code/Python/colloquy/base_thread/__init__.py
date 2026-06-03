# -*- coding: utf-8 -*-
# colloquy/base_thread/__init__.py
import traceback
from time import time, sleep

import inspect
from pathlib import Path
from urllib.parse import unquote
import urllib.parse
import socket
from colloquy.base import Base
from threading import Thread, Event, Lock
from .thread_errors import ThreadErrors

class BaseThread(Base):
    
    _shutdown = Event()

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._colloquy = None
        self._hardware = None
        self._started_at = None
        self._started_by = None
        self._thread_errors = ThreadErrors(owner=self)

        self._children = set()

        self._thread = None
        self._stop_event = Event()
        self._lock = Lock()

        self["start"] = self.start_command
        self["stop"] = self.stop_command
        self[self.thread_errors.name] = self.thread_errors

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
    def thread_errors(self):
        return self._thread_errors

    @property
    def children(self):
        return self._children

    @property
    def colloquy(self):
        if self._colloquy is None:
            self._colloquy = self.owner.colloquy
        return self._colloquy

    @property
    def hardware(self):
        if self._hardware is None:
            self._hardware = self.colloquy.hardware
        return self._hardware

    @property
    def is_started(self):
        if self._thread is None:
            return False
        return self._thread.is_alive()
    
    def append_error(self, value):
        raise NotImplementedError

    def leave_some_time_to_other_threads(self):
        sleep(0.01)

    def start_command(self, request=None):
        self.start(started_by=None)

    def stop_command(self, request=None):
        self.stop()
        self.join()

    def start(self, started_by=None):
        if started_by is not None:
            if self in started_by.children:
                raise NotImplementedError(f"Should be deleted when stop.")
            started_by.children.add(self)
        if self._shutdown.is_set():
            return
        if self.thread_errors:
            raise NotImplementedError(f"Implement a clear error! ({self=})")
            return
        if self.is_started:
            return
        self.log(f"{started_by} is starting {self}.")
        self._started_at = time()
        self._started_by = started_by
        self._stop_event.clear()
        self._thread = thread = Thread(target=self.run, name=self.path.as_posix())
        self.all_threads.add(self)
        thread.start()

    def shutdown(self):
        self._shutdown.set()
        if self._thread is None:
            return
        self.log(f"Shuting down {self}.")

    def stop(self):
        if self._thread is None:
            return
        self.log(f"Stopping {self}.")
        self._stop_event.set()
        # self._thread.join()

    def join(self):
        if self._thread is not None:
            self._thread.join()
        for thread in self.children:
            thread.join()

    def join_all(self):
        for thread in self.all_threads:
            thread.join()

    def run(self, run_with=None):
        self.log(f"Executing {self}.run().")
        if run_with is None:
            return self._run_in_context()
        with run_with:
            self._run_in_context()

    def loop(self):
        raise NotImplementedError(f"User defined! ({self=})")

    def setup(self):
        raise NotImplementedError(f"User defined! ({self=})")

    def setdown(self):
        raise NotImplementedError(f"User defined! ({self=})")

    def _run_in_context(self):
        self.log(f"{self} is started.")
        try:
            self._run_unsafe()
        except Exception as error:  
            print(f"error in {self=}")
            error_text = "".join(traceback.format_exception(error))
            self.log(error_text)
            self.thread_errors.append(error)
        finally:
            self.setdown()
            if self._started_by is not None:
                self._started_by.children.discard(self)

    def _run_unsafe(self):
        self.setup()
        while True:
            if self._break_condition():
                break                
            self.loop()
            sleep(0.01)

    def _break_condition(self):
        if self.thread_errors:
            self.log(f"Break condition: {self.thread_errors=}.")
            return True
        if self._stop_event.is_set():
            self.log(f"Break condition: {self._stop_event.is_set()=}.")
            return True
        if self._shutdown.is_set():
            self.log(f"Break condition: {self._shutdown.is_set()=}.")
            return True
            
        if self._started_by is not None:
            if not self._started_by.is_started:
                self.log(f"Break condition: {not self._started_by.is_started=}.")
                return True
        return False
    
    def snapshot(self, path):
        states = super().snapshot(path=path)
        _path = states["path"]
        if self.is_started:
            states["stop"] = self.stop
        else:
            states["start"] = self.start
        
        if self.thread_errors:
            states[self.thread_errors.name] = self.thread_errors.snapshot(path=_path)
        return states
        


