from pathlib import Path
from colloquy.base_thread import BaseThread
from datetime import datetime

from threading import Event
import traceback
from threading import Thread, Event, Lock
from time import sleep, time
from .html import HTML

class TestWithOnlyFemaleMoving(BaseThread):

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request
        
        self._start_time = None
        self._timelap = None
        self._duration = 1*60 # test running 'self._duration' seconds
        
        
        self._dir_path = Path("local") / self.name
        if not self._dir_path.exists():
            self._dir_path.mkdir()
            
        self._file_path = None
        self._file = None


    @property
    def name(self):
        duration = self._timelap_to_string(self._duration)
        return f"test with only female moving for {duration}"

    @property
    def html(self):
        return self._html

    def run(self):        
        now = datetime.now()
        self._file_path = self._dir_path / f"{now.year}_{now.month:02}_{now.day:02}_{now.hour:02}h_{now.minute:02}min_{now.second:02}s.csv"
        run_with = self._file = self._file_path.open("a")      
        super().run(run_with=run_with)
        
    def setup(self):            
        self._file.write("seconds, value" + "\n")
        self._start_time = time()
        self.hardware.male1.turn_to_origin()
        self.hardware.male1.dxl.wait_for_servo()
        self.hardware.female1.turn_back_and_forth.start(started_by=self)
        self.hardware.male1.neopixels.ring.on()

    def setdown(self):
        self._start_time  = None
        self.hardware.female1.turn_back_and_forth.stop()
        self.hardware.male1.neopixels.ring.off()

    def loop(self):   
        timestamp = time() - self._start_time
        value = self.hardware.female1.light_sensor.read()        
        self._file.write(f"{timestamp}, {value}" + "\n")
        if timestamp > self._duration:
            self.stop()
    
    def snapshot(self, path):
        states = super().snapshot(path=path)
        _path = states["path"]
        if self._start_time is not None:
            seconds_elapsed = time() - self._start_time   
            states["running during"] = {
                "path": _path + ("running during", ),
                "name": "running during",
                "value": self._timelap_to_string(seconds_elapsed=seconds_elapsed),
                }
        return states 
    
    def _timelap_to_string(self, seconds_elapsed):
        seconds_elapsed = round(seconds_elapsed)
        if seconds_elapsed > 60:
            minutes = seconds_elapsed // 60
            seconds = seconds_elapsed % 60
            tokens = [f"{minutes}min"]
            if seconds != 0:
                tokens.append(f"{seconds}s")
            seconds_elapsed_as_string = " ".join(tokens)
        else:
            seconds_elapsed_as_string = f"{seconds_elapsed}s"
            
        return seconds_elapsed_as_string
        