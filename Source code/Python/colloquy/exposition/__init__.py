from time import time, sleep
import traceback
from colloquy.base_thread import BaseThread
from pathlib import Path
import traceback
from threading import Thread, Event, Lock
from .html import HTML


class Exposition(BaseThread):

    def __init__(self, owner):
        super().__init__(owner)
        self._html = HTML(owner=self)
        self._hardware = self.owner.hardware

        self._thread = None

        self[self.html.name] = self.html.handle_request

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
        
    def open(self):
        self._is_opened = True 
        
    def close(self):
        self._is_opened = False

    def setup(self):
        self.hardware.start(started_by=self)

    def loop(self):
        if not self.hardware.is_started:
            self.stop()

    def setdown(self):
        if self.thread_errors:
            self.hardware.shutdown()
        self.hardware.stop()
    
    # def snapshot(self, path):
        # path = path + (self.name,)
        # states = {
            # "path": path,
            # "name": self.name,
            # "open": self.open,
            # "close": self.close,
        # }
        # return states 
    
    @property
    def snapshot_children(self):
        children = {}
        return children