# from collo.thread import Thread
from colloquy.neopixel import Neopixel
from colloquy.thread_element import ThreadElement
from .ring import Ring
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
        self.ring = Ring(owner=self, name="ring")
        # self._drive = Neopixel(owner=self, name="drive")
        self._bottom_neopixel_o = BottomNeopixelO(owner=self,)
        self._bottom_neopixel_p = BottomNeopixelP(owner=self,)
        self._beam = Beam(owner=self)
        self.light_patterns = {}
        for k, v in LIGHT_PATTERNS[owner.name].items():
            # The deque with max_len will act as circular list
            self.light_patterns[k] = deque(v, maxlen=len(v))
        # self._blink = Blink(owner=self)

    @property
    def bottom_neopixel_o(self):
        return self._bottom_neopixel_o

    @property
    def bottom_neopixel_p(self):
        return self._bottom_neopixel_p

    @property
    def drive(self):
        raise NotImplementedError
        return self._drive

    @property
    def beam(self):
        return self._beam

    @property
    def arduino_manager(self):
        return self._owner.arduino_manager

    @property
    def drives(self):
        return self._owner.drives

    @property
    def segments(self):
        return self._owner.segments

    def off(self):
        self.ring.off()
        self.bottom_neopixel_o.off()
        self.bottom_neopixel_p.off()
    
    def on(self):
        self.ring.on()
        self.bottom_neopixel_o.on()
        self.bottom_neopixel_p.on()

    def __enter__(self):
        self.stop_event.clear()

    def _loop(self):
        pass
        # self.sleep_min()

    def stop(self):
                
        if self._is_started:      
            self.off()
            
        ThreadElement.stop(self)

class Beam(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name=f"beam")        

    def __enter__(self):
        self.stop_event.clear()
        self.owner.ring.on()     
        
    def __exit__(self, exc_type, exc_value, traceback_obj):
        self.owner.ring.off()
        return ThreadElement.__exit__(self, exc_type, exc_value, traceback_obj)

    def _loop(self):
        pass
        
        



class BottomNeopixelO(Neopixel):

    def __init__(self, owner):
        Neopixel.__init__(self, owner=owner, name="o_drive")
    
    def set_test_default(self):
        self.configure(red=0, green=255, blue=0, white=0, brightness=255)
        self.on()


class BottomNeopixelP(Neopixel):

    def __init__(self, owner):
        Neopixel.__init__(self, owner=owner, name="p_drive")  
    
    def set_test_default(self):
        self.configure(red=255, green=0, blue=0, white=0, brightness=255)
        self.on()