from colloquy.wsgi.root.item import Item
from .u2d2 import U2D2
from .arduino import Arduino
from .female import Female


class Hardware(Item):
    
    def __init__(self, owner, ):
        Item.__init__(self, owner)
        self._arduino = Arduino(owner=self)
        self._u2d2 = U2D2(owner=self)
        self._bar = None
        
        self._threads = set()
        
        self._mirrors = []
        self._males = []
        self._bodies = []
        self._speakers = []
        self._females = []
        self._moving_elements = []
        
        self._female1 = Female(owner=self, name="female1")
        self._female2 = Female(owner=self, name="female2")
        self._female3 = Female(owner=self, name="female3")

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