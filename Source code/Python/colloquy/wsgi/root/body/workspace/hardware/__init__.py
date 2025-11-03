from .u2d2 import U2D2
from .arduino import Arduino
from colloquy.wsgi.root.body.workspace.item import Item, Action
from .female import Female
from .html import HTML
from .neopixels import Neopixels
from .commands import Commands
from .logger import Logger


class Hardware(Item):
    
    def __init__(self, owner, ):
        Item.__init__(self, owner)
        self._opened = None
        self._html = HTML(owner=self)
        self._commands = Commands(owner=self)
        self._log = Logger(owner=self)
        
        
        self._arduino = Arduino(owner=self)
        self._u2d2 = U2D2(owner=self)
        self._neopixels = Neopixels(owner=self)
        self._bar = None
        
        # self._threads = set()
        
        self._mirrors = []
        self._males = []
        self._bodies = []
        self._speakers = []
        self._females = []
        self._moving_elements = []
        
        self._female1 = Female(owner=self, name="female1")
        self._female2 = Female(owner=self, name="female2")
        self._female3 = Female(owner=self, name="female3")

    def __call__(self):
        if not self.is_opened:
            self.open()

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
        return "hardware"

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
    def moving_elements(self):
        return self._moving_elements
    
    @property
    def neopixels(self):
        return self._neopixels
        
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