from pathlib import Path
from colloquy.base_thread import BaseThread
from datetime import datetime
from colloquy.utils import timelap_to_string

from threading import Event
import traceback
from threading import Thread, Event, Lock
from time import sleep, time
from .html import HTML
from ..utils import read_and_store, post_process, plot_as_svg

class TestWithFemaleMaleAndBarMoving(BaseThread):

    def __init__(self, owner, result_folder, test_duration):
        super().__init__(owner=owner)
        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request
        
        self._start_time = None
        self._timelap = None
        self._duration = test_duration # test running 'self._duration' seconds
        
        self._sensors_read = tuple(female.light_sensor.read for female in self.hardware.females)
        
        
        self._dir_path = result_folder / self.name
        if not self._dir_path.exists():
            self._dir_path.mkdir()
            
        self._file_path = None
        self._file = None


    @property
    def name(self):
        duration = timelap_to_string(self._duration)
        return f"test with female male and bar moving for {duration}"

    @property
    def html(self):
        return self._html

    @property
    def duration(self):
        return self._duration

    def run(self):        
        now = datetime.now()
        self._file_path = self._dir_path / f"{now.year}_{now.month:02}_{now.day:02}_{now.hour:02}h_{now.minute:02}min_{now.second:02}s.csv"
        run_with = self._file = self._file_path.open("a")      
        super().run(run_with=run_with)
        
        file_path = self._file_path
        output=file_path.with_name(f"post {file_path.stem}.csv")
        post_process(file=file_path, output=output)
        plot_as_svg(path=output)
        
    def setup(self):            
        self._file.write("seconds, female1, female2, female3" + "\n")
        self._start_time = time()
        
        self.hardware.bar.move_male1_in_front_of_female1_and_wait()
        
        self.hardware.male1.neopixels.ring.on()
        self.hardware.female1.turn_back_and_forth.start(started_by=self)
        self.hardware.male1.turn_back_and_forth.start(started_by=self)
        self.hardware.bar.turn_back_and_forth_around_f1.start(started_by=self)

    def setdown(self):
        self._start_time  = None
        self.hardware.female1.turn_back_and_forth.stop()
        self.hardware.male1.turn_back_and_forth.stop()
        self.hardware.male1.neopixels.ring.off()
        self.hardware.bar.turn_back_and_forth_around_f1.stop()

    def loop(self):   
        return read_and_store(
            start_time=self._start_time, 
            sensors_read=self._sensors_read,
            file=self._file,
            stop=self.stop,
            duration=self._duration,
            ) 
        # timestamp = time() - self._start_time
        # value = self.hardware.female1.light_sensor.read()  
        # self._file.write(f"{timestamp}, {value}" + "\n")
        # if timestamp > self._duration:
            # self.stop()
    
    def snapshot(self, path):
        states = super().snapshot(path=path)
        _path = states["path"]
        if self._start_time is not None:
            seconds_elapsed = time() - self._start_time   
            states["running during"] = {
                "path": _path + ("running during", ),
                "name": "running during",
                "value": timelap_to_string(seconds_elapsed=seconds_elapsed),
                }
            states["progress"] = {
                "path": _path + ("progress", ),
                "name": "progress",
                "value": f"{round(100*seconds_elapsed/self._duration)}%",
                }
        return states 
        