from colloquy.wsgi.root.body.workspace.hardware.neopixel import Neopixel
from colloquy.wsgi.root.body.item import Item
from colloquy.wsgi.root.html_item import HtmlItem

from pathlib import Path
from threading import Event
        
        
    

class HeadFemaleNeopixel(Neopixel):

    def __init__(self, owner):
        Neopixel.__init__(self, owner=owner, name="head neopixel")
        self._body = owner
    
    def set_test_default(self):
        self.configure(red=0, green=255, blue=0, white=0, brightness=255)
        self.on()


class BodyFemaleNeopixel(Item):

    def __init__(self, owner):
        Item.__init__(self, owner=owner, ) 
        self._arduino = owner.arduino
        self._o_neopixel = BodyFemaleONeopixel(owner=self)
        self._p_neopixel = BodyFemalePNeopixel(owner=self)
        self._neopixels = [
            self.o_neopixel,
            self.p_neopixel,
        ]
        

    @property
    def arduino(self):
        return self._arduino
        
        
    @property
    def neopixels(self):
        return self._neopixels
    
    @property
    def name(self):
        return "body neopixel"
    
    @property
    def o_neopixel(self):
        return self._o_neopixel
    
    @property
    def p_neopixel(self):
        return self._p_neopixel
    
    @property
    def segments(self):
        return self.owner.segments
    
    @property
    def elements(self):
        return self.owner.elements
    
    @property
    def hardware(self):
        return self.owner.hardware
    
    @property
    def arduino_manager(self):
        return self.owner.arduino_manager
    
    def open(self):
        self.o_neopixel.open()
        self.p_neopixel.open()
    
    def on(self):
        self.o_neopixel.on()
        self.p_neopixel.on()
    
    def off(self):
        self.o_neopixel.off()
        self.p_neopixel.off()


class FeetFemaleNeopixel(Neopixel):

    def __init__(self, owner):
        Neopixel.__init__(self, owner=owner, name="feet neopixel")  
        self._body = owner
    
    def set_test_default(self):
        self.configure(red=0, green=0, blue=255, white=0, brightness=255)
        self.on()


class BodyFemaleONeopixel(Neopixel):

    def __init__(self, owner):
        Neopixel.__init__(self, owner=owner, name="O")  
        self._body = owner.owner
    
    def set_test_default(self):
        self.configure(red=125, green=125, blue=0, white=0, brightness=255)
        self.on()
        
class BodyFemalePNeopixel(Neopixel):

    def __init__(self, owner):
        Neopixel.__init__(self, owner=owner, name="P")  
        self._body = owner.owner
    
    def set_test_default(self):
        self.configure(red=125, green=0, blue=125, white=0, brightness=255)
        self.on()