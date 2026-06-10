from pathlib import Path
from colloquy.base_thread import BaseThread

from threading import Event
import traceback
from threading import Thread, Event, Lock
from time import sleep, time
from .html import HTML

class TestReadSensor(BaseThread):

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request
        
        
        sensor = self.hardware.female1.light_sensor
        self[sensor.name] = sensor
        
        ring = self.hardware.male1.neopixels.ring
        self[ring.name] = ring
               
        
        self._start_time = None
        self._timelap = None


    @property
    def name(self):
        return "test read sensor"

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
        sensor = self.hardware.female1.light_sensor
        states[sensor.name] = sensor.snapshot(_path)
        
        ring = self.hardware.male1.neopixels.ring
        states[ring.name] = ring.snapshot(_path)
        
        return states 
        