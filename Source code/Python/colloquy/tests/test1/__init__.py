from pathlib import Path
from colloquy.base import Base
from utils import CustomDoc
from threading import Event
import traceback
from threading import Thread, Event, Lock
from time import sleep
from .html import HTML

class Test1(Base):

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._html = HTML(owner=self)
        self._is_started = False
        self._thread = None
        self._loop_index = 0
        self._stop_event = Event()
        
        self[self.html.name] = self.html.handle_request
        self["start"] = self.start
        self["stop"] = self.stop

    def __call__(self, request):
        request = Path(request)
        if not request.parts:
            raise NotImplementedError
            
        key, *leftover = request.parts
        
        if key in self:
            self[key](request="/".join(leftover))
            return
            
        raise NotImplementedError(f"{key=}, {leftover=}, in {self=}") 

    @property
    def is_started(self):
        if self._thread is None:
            return False
        return self._thread.is_alive()

    @property
    def colloquy(self):
        return self.owner.colloquy 

    @property
    def hardware(self):
        return self.colloquy.hardware 

    @property
    def name(self):
        return "test1" 

    @property
    def html(self):
        return self._html

    def start(self, request=None):
        self._stop_event.clear()
        self._loop_index = 0
        self._thread = thread = Thread(target=self.run, name=self.path.as_posix())
        thread.start()

    def stop(self, request=None):
        if self._thread is not None:
            return
        self._stop_event.set()
        self._thread.join()
    
    def run(self):
        try:
            self._run_unsafe()
        except Exception as error:
            self._error = error
            raise 
    
    def _run_unsafe(self):
        stop_event = self._stop_event.is_set
        hardware = self.hardware
        neopixels = hardware.neopixels
        
        if stop_event():
            return
        
        with hardware.arduino:        
            for neopixel in neopixels:
                neopixel.off()
            
            for i in range(10):
                for neopixel in neopixels:
                    neopixel.set_test_default()
                    neopixel.on()
                
                for e in range(10):
                    sleep(0.1)       
                    if stop_event():
                        return
                
                for neopixel in neopixels:
                    neopixel.off()
                    
                for e in range(5):
                    sleep(0.1)       
                    if stop_event():
                        return
        
        