# from colloquy.wsgi.root.body.action_item import ActionItem
import traceback
from colloquy.base import Base
from pathlib import Path
import traceback
from time import time
from colloquy.utils import timelap_to_string

from colloquy.base_thread import BaseThread

#from .handle_html import HTML
from .test_with_only_female_moving import TestWithOnlyFemaleMoving
from .test_with_female_and_male_moving import TestWithFemaleAndMaleMoving
from .test_with_female_male_and_bar_moving import TestWithFemaleMaleAndBarMoving
from .test_with_everything_moving import TestWithEveryThingMoving

class TestLightSensorValues(BaseThread):

    def __init__(self, owner, result_folder):
        super().__init__(owner)
        # self.opened = None
        self._queue = None
        self._running_test = None
        self._start_time = None
        
        if self.name not in self.owner.params:
            self._params = self.owner.params[self.name] = {}
        else:
            self._params = self.owner.params[self.name]
        
        test_duration = 30 # seconds

        # self._html = HTML(owner=self)
        self.test_with_only_female_moving = TestWithOnlyFemaleMoving(
            owner=self, 
            result_folder=result_folder, 
            test_duration=test_duration,
            )
        self.test_with_female_and_male_moving = TestWithFemaleAndMaleMoving(
            owner=self, 
            result_folder=result_folder, 
            test_duration=test_duration,
            )
        self.test_with_female_male_and_bar_moving = TestWithFemaleMaleAndBarMoving(
            owner=self, 
            result_folder=result_folder, 
            test_duration=30 #15*60,
            )
        self.test_with_everything_moving = TestWithEveryThingMoving(
            owner=self, 
            result_folder=result_folder, 
            test_duration=30*60,
            )
        self._hardware = self.owner.hardware

        # self[self.html.name] = self.html.handle_request
        # self.add(self.test1)

        self._threaded_tests = [
            self.test_with_only_female_moving,
            self.test_with_female_and_male_moving,
            self.test_with_female_male_and_bar_moving,
            self.test_with_everything_moving,
            ]
        
        self._duration = sum(test.duration for test in self._threaded_tests)


    @property
    def params(self):
        return self._params

    @property
    def colloquy(self):
        return self.owner.colloquy
        
    @property
    def html(self):
        return self._html

    @property
    def name(self):
        return "test light sensor values"

    @property
    def workspace(self):
        return self

    @property
    def hardware(self):
        return self._hardware
        
    def setup(self):   
        self._start_time = time()         
        self._queue = list(self._threaded_tests)
        self._running_test = test = self._queue.pop(0)
        test.start(started_by=self)

    def setdown(self):
        self._start_time  = None
        self._queue = None
        self._running_test = None
        self.hardware.male1.neopixels.ring.off()
        for test in self._threaded_tests:
            test.stop()
            test.join()
        for test in self._threaded_tests:
            test.plot()

    def loop(self):   
        if self._running_test.is_started:
            return    
        if not self._queue:
            self.stop()
            return
        self._running_test = test = self._queue.pop(0)
        test.start(started_by=self)
    
    # def snapshot(self, path):
        # states = super().snapshot(path=path)
        # _path = states["path"]
        # if self._start_time is not None:
            # seconds_elapsed = time() - self._start_time   
            # states["running during"] = {
                # "path": _path + ("running during", ),
                # "name": "running during",
                # "value": timelap_to_string(seconds_elapsed=seconds_elapsed),
                # }
            # states["progress"] = {
                # "path": _path + ("progress", ),
                # "name": "progress",
                # "value": f"{round(100*seconds_elapsed/self._duration)}%",
                # }
            # states["total duration"] = {
                # "path": _path + ("total duration", ),
                # "name": "duration",
                # "value": timelap_to_string(seconds_elapsed=self._duration),
                # }
        # for test in self._threaded_tests:            
            # states[test.name] = test.snapshot(path=_path)
        # return states 
    
    @property
    def snapshot_children(self):
        children = {}
        for test in self._threaded_tests:  
            children[test.name] = test
        return children
    
    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        if self._start_time is not None:
            seconds_elapsed = time() - self._start_time   
            states["running during"] = {
                "path": path + ("running during", ),
                "name": "running during",
                "value": timelap_to_string(seconds_elapsed=seconds_elapsed),
                }
            states["progress"] = {
                "path": path + ("progress", ),
                "name": "progress",
                "value": f"{round(100*seconds_elapsed/self._duration)}%",
                }
            states["total duration"] = {
                "path": path + ("total duration", ),
                "name": "duration",
                "value": timelap_to_string(seconds_elapsed=self._duration),
                }
        super()._snapshot_if_opened(path)
        return states