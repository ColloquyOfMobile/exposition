# from collo.thread import Thread
from colloquy.neopixel import Neopixel
from colloquy.thread_element import ThreadElement
from pathlib import Path
from threading import Event
from collections import deque
from time import time, sleep

# During search the male blinks.
# The blink pattern define 2 things:
# - the male identity: 1 or 2
# - which kind of interation the male is look for (drive state): "O" or "P" or both
# Extracted from TJ's arduino code "logic35_system.ino, line 87."
LIGHT_PATTERNS = {
    "male1": {
        tuple():     (1, 1, 0, 0, 1, 1, 0, 0, 0, 1),
        ("O",):      (1, 1, 0, 0, 0, 0, 0, 1, 1, 1),
        ("P",):      (1, 1, 0, 0, 0, 0, 1, 1, 1, 0),
        ("O", "P"): (1, 1, 0, 0, 0, 1, 0, 1, 0, 1),
    },
    "male2": {
        tuple():     (1, 1, 0, 0, 1, 1, 1, 0, 0, 0),
        ("O",):      (1, 1, 0, 0, 0, 1, 1, 1, 0, 0),
        ("P",):      (1, 1, 0, 0, 1, 0, 0, 0, 1, 1),
        ("O", "P"): (1, 1, 0, 0, 1, 0, 1, 0, 1, 0),
    }
}

class BodyNeopixels(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, name="body", owner=owner)
        self.ring = Neopixel(owner=self, name="ring")
        self.drive = Neopixel(owner=self, name="drive")
        self._beam = Beam(owner=self)
        self.light_patterns = {}
        for k, v in LIGHT_PATTERNS[owner.name].items():
            # The deque with max_len will act as circular list
            self.light_patterns[k] = deque(v, maxlen=len(v))
        # self._blink = Blink(owner=self)

    # @property
    # def blink(self):
        # return self._blink

    @property
    def beam(self):
        return self._beam

    @property
    def arduino_manager(self):
        return self._owner.arduino_manager

    @property
    def drives(self):
        return self._owner.drives

    def off(self):
        self.ring.off()
        self.drive.off()

    def __enter__(self):
        self.stop_event.clear()

    def _loop(self):
        pass
        # self.sleep_min()

    def stop(self):
        self.off()
        ThreadElement.stop(self)

class Beam(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name=f"beam")        

    def __enter__(self):
        print(f"The {self.owner.owner.name} is beaming...")
        self.stop_event.clear()
        self.owner.ring.on()     
        
    def __exit__(self, exc_type, exc_value, traceback_obj):
        self.owner.ring.off()
        return ThreadElement.__exit__(self, exc_type, exc_value, traceback_obj)

    def _loop(self):
        pass
