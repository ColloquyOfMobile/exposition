# from collo.thread_driver import ThreadDriver
from colloquy.neopixel_driver import NeopixelDriver
from colloquy.thread_driver import ThreadDriver
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

class BodyNeopixels(ThreadDriver):

    def __init__(self, owner):
        ThreadDriver.__init__(self, name="body", owner=owner)
        self.ring = NeopixelDriver(owner=self, name="ring")
        self.drive = NeopixelDriver(owner=self, name="drive")
        self.light_patterns = {}
        for k, v in LIGHT_PATTERNS[owner.name].items():
            # The deque with max_len will act as circular list
            self.light_patterns[k] = deque(v, maxlen=len(v))
        self._timestamp = None

    # @property
    # def name(self):
        # return self._owner.name

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
        light_pattern = self.light_patterns[self.drives.state]
        self._timestamp = time()
        value = light_pattern.popleft()
        light_pattern.append(value)
        self.ring.set(value)

    def _loop(self):
        if (time() - self._timestamp) > 0.5:
            light_pattern = self.light_patterns[self.drives.state]
            value = light_pattern.popleft()
            light_pattern.append(value)
            self.ring.set(value)
            self._timestamp = time()
        # self.sleep_min()

    def stop(self):
        self.ring.off()
        self.drive.off()
        ThreadDriver.stop(self)