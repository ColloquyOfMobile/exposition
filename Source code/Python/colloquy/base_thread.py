from time import time, sleep
from utils import CustomDoc
import inspect
from pathlib import Path
from urllib.parse import unquote
import urllib.parse
import socket
from colloquy.base import Base
from threading import Thread, Event, Lock

class BaseThread(Base):

    def __init__(self, owner):
        super().__init__(owner=owner)   
        self._colloquy = None
        self._hardware = None
        self._started_at = None
        self._started_by = None      
        self._child_errors = []
        
        self._thread = None
        self._stop_event = Event()
        
        self["start"] = self.start_command
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

    def start_command(self, request=None):
        self.start(started_by=None)

    def start(self, started_by):
        self.log(f"Start {self}.")   
        self._started_at = time()
        self._started_by = started_by
        self._stop_event.clear()
        self._thread = thread = Thread(target=self.run, name=self.path.as_posix())
        thread.start()

    def stop(self, request=None):
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join()

    def run(self):     
        self.log(f"{self} is started.")   
        try:
            self._run_unsafe()
        except Exception as error:
            self._started_by.add_error(origin=self, error=error)

    def add_error(self, origin, error):        
        self.child_errors.append(
            (origin, error)
        )
    

    