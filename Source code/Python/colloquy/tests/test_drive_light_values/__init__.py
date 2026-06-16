from pathlib import Path
from colloquy.base_thread import BaseThread
from colloquy.utils import timelap_to_string

from threading import Event
import traceback
from threading import Thread, Event, Lock
from time import sleep, time
from .html import HTML

class TestDriveLightValues(BaseThread):

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request
        
        for drive in self.hardware.drives:
            self[drive.name] = drive
        
        self._start_time = None
        self._timelap = None


    @property
    def name(self):
        return "test drives light values"

    @property
    def html(self):
        return self._html
        
    def setup(self):        
        self._start_time = time()
        
        for drive in self.hardware.drives:
            drive.start(started_by=self)
            
        for neopixel in self.hardware.neopixels:
            neopixel.on()

    def setdown(self):
        for drive in self.hardware.drives:
            drive.stop()
        for neopixel in self.hardware.neopixels:
            neopixel.off()

    def loop(self):    
        self._timelap= time() - self._start_time    
        if all(drive.value == 100 for drive in self.hardware.drives):
            self.stop()
        return
    
    def snapshot(self, path):
        states = super().snapshot(path=path)
        _path = states["path"]
        if self._timelap is not None:
            states["timelap"] = {
                "path": _path + ("timelap", ),
                "name": "timelap",
                "value": timelap_to_string(seconds_elapsed=self._timelap),
                }
        for drive in self.hardware.drives:
            name = f"{drive.body.name}'s {drive.name} drive"
            states[drive.name] = drive.snapshot(path=_path)
        return states 
        