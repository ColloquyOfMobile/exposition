# from colloquy.wsgi.root.body.action_item import ActionItem
import traceback
from colloquy.base import Base
from pathlib import Path
import traceback
from time import time

from colloquy.base_thread import BaseThread

from .html import HTML
from .test_with_only_female_moving import TestWithOnlyFemaleMoving
from .test_with_female_and_male_moving import TestWithFemaleAndMaleMoving

class TestLightSensorValues(BaseThread):

    def __init__(self, owner):
        super().__init__(owner)
        # self.opened = None
        self._queue = None
        self._running_test = None

        self._html = HTML(owner=self)
        self.test_with_only_female_moving = TestWithOnlyFemaleMoving(owner=self)
        self.test_with_female_and_male_moving = TestWithFemaleAndMaleMoving(owner=self)
        self._hardware = self.owner.hardware

        self[self.html.name] = self.html.handle_request
        # self.add(self.test1)

        self._threaded_tests = [
            self.test_with_only_female_moving,
            self.test_with_female_and_male_moving,
            ]

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
        self._queue = None
        self._running_test = None
        self.hardware.male1.neopixels.ring.off()

    def loop(self):   
        if self._running_test.is_started:
            return    
        if not self._queue:
            self.stop()
            return
        self._running_test = test = self._queue.pop(0)
        test.start(started_by=self)
        

    # def stop(self):
        # for test in self._threaded_tests:
            # test.stop()
        # super
    
    def snapshot(self, path):
        states = super().snapshot(path=path)
        _path = states["path"]
        for test in self._threaded_tests:            
            states[test.name] = test.snapshot(path=_path)
        return states 