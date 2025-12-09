from .u2d2 import U2D2
from .arduino import Arduino
from colloquy.base import Base
from .female import Female
from pathlib import Path
# from .html import HTML
from .neopixels import Neopixels
from .commands import Commands
from .logger import Logger


class Hardware(Base):
    
    def __init__(self, owner, surname=""):
        """Use the surname if you want to instanciate 2 instances of hardware. Log file path are compute through names, two object can write to the same file. Mainly intended for tests."""
        
        self._surname = surname
        
        super().__init__(owner)   
        self._log = owner.log     
        
        self._opened = None
        # self._html = HTML(owner=self)
        self._commands = Commands(owner=self)
        # self._log = Logger(owner=self)
        
        
        self._arduino = Arduino(owner=self)
        self._u2d2 = U2D2(owner=self)
        # self._neopixels = Neopixels(owner=self)
        self._bar = None
        
        # self._threads = set()
        
        self._mirrors = []
        self._males = []
        self._speakers = []
        self._moving_elements = []
        
        self._female1 = Female(owner=self, id_number=1)
        # self._female2 = Female(owner=self, name="female2")
        # self._female3 = Female(owner=self, name="female3")
        self._females = [
            self._female1,
            # self._female2,
            # self._female3,
            ]
            
        self[self.arduino.name] = self.arduino
        
        for female in self._females:
            self[female.name] = female

    

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
    def colloquy(self):
        return self.owner.colloquy

    @property
    def opened(self):
        return self._opened

    @opened.setter
    def opened(self, value):
        # Value is None only in a Close(), this is to avoid recursion.
        if value is not None:
            if self._opened is not None:
                self._opened.close()
                
        self._opened = value

    @property
    def html(self):
        return self._html   

    @property
    def log(self):
        return self._log

    @property
    def name(self):
        return "hardware" # + " " + self._surname

    @property
    def arduino(self):
        return self._arduino

    @property
    def u2d2(self):
        return self._u2d2

    @property
    def bar(self):
        return self._bar

    @property
    def mirrors(self):
        return self._mirrors

    @property
    def males(self):
        return self._males

    @property
    def speakers(self):
        return self._speakers

    @property
    def females(self):
        return self._females

    @property
    def female1(self):
        return self._female1

    @property
    def female2(self):
        return self._female2

    @property
    def female3(self):
        return self._female3

    @property
    def moving_elements(self):
        return self._moving_elements
    
    @property
    def neopixels(self):
        # return self._neopixels
        
        neopixels = []
        for body in self.bodies:
            neopixels.extend(body.neopixels)
        return neopixels
    
    @property
    def bodies(self):
        bodies = []
        for body in self.females:
            bodies.append(body)
        for body in self.males:
            bodies.append(body)
        return bodies
    
    def shutdown(self):
        with self.arduino:
            for neopixel in self.neopixels:
                neopixel.off()