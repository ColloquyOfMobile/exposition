from pathlib import Path
from colloquy.base_thread import BaseThread

from threading import Event
import traceback
from threading import Thread, Event, Lock
from time import sleep, time
from .html import HTML

class TestMalePatterns(BaseThread):

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request
        
        self._blink_handlers = []
        for male in self.hardware.males:
            blink_handler = male.search.blink
            self[blink_handler.name] = blink_handler
            self._blink_handlers.append(blink_handler)        
        
        self._start_time = None
        self._timelap = None


    @property
    def name(self):
        return "test male pattern"

    @property
    def html(self):
        return self._html
        
    def setup(self):        
        self._start_time = time()
        
        for blink_handler in self._blink_handlers:
            blink_handler.start(started_by=self)

    def setdown(self):
        for blink_handler in self._blink_handlers:
            blink_handler.stop()

    def loop(self):       
        if any(not blink_handler.is_started for blink_handler in self._blink_handlers):
            self.stop()
        return
    
    def snapshot(self, path):
        states = super().snapshot(path=path)
        _path = states["path"]
        for blink_handler in self._blink_handlers:
            states[blink_handler.name] = blink_handler.snapshot(path=_path)
        return states 
        