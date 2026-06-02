from pathlib import Path
from colloquy.base_thread import BaseThread

from threading import Event
import traceback
from threading import Thread, Event, Lock
from time import sleep
from .html import HTML

class TestDriveLightValues(BaseThread):

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request


    @property
    def name(self):
        return "test drives light values"

    @property
    def html(self):
        return self._html
        
    def setup(self):
        for drive in self.hardware.drives:
            drive.start(started_by=self)
        # raise NotImplementedError(f"{self.hardware.drives=}")
        for neopixel in self.hardware.neopixels:
            neopixel.on()

    def setdown(self):
        for drive in self.hardware.drives:
            drive.stop()
        for neopixel in self.hardware.neopixels:
            neopixel.off()

    def loop(self):
        return
    
    def snapshot(self, path):
        states = super().snapshot(path=path)
        _path = states["path"]
        if self.is_started:
            
        for drive in self.hardware.drives:
            states[name] = drive.snapshot(path=_path)
        return states 