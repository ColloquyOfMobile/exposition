from colloquy.hardware.neopixel import Neopixel
# from colloquy.hardware.female.item import Item
# from colloquy.wsgi.root.html_item import HtmlItem
from colloquy.base import Base

from pathlib import Path
from threading import Event
        
        
    

class Head(Neopixel):

    def __init__(self, owner):
        super().__init__(owner=owner, name="head")
        self._body = owner
        self.white.value = 255
    
    def set_test_default(self):
        self.configure(red=0, green=255, blue=0, white=0, brightness=255)

    @property
    def arduino_path(self):
        return Path(f"f{self.owner.id_number}/{self.name}")


class Feet(Neopixel):

    def __init__(self, owner):
        super().__init__(owner=owner, name="feet")  
        self._body = owner
        self.brightness.value = 100
        
    @property
    def arduino_path(self):
        return Path(f"f{self.owner.id_number}/{self.name}")
    
    def set_test_default(self):
        self.configure(red=0, green=0, blue=255, white=0, brightness=255)
        self.on()


class BodyO(Neopixel):

    def __init__(self, owner):
        super().__init__(owner=owner, name="bodyO")  
        self._body = owner
        self.color = self.orange
        
    @property
    def arduino_path(self):
        return Path(f"f{self.owner.id_number}/{self.name}")
    
    def set_test_default(self):
        self.configure(red=125, green=125, blue=0, white=0, brightness=255)
        self.on()
        
class BodyP(Neopixel):

    def __init__(self, owner):
        super().__init__(owner=owner, name="bodyP")  
        self._body = owner
        self.color = self.puce

    @property
    def arduino_path(self):
        return Path(f"f{self.owner.id_number}/{self.name}")
    
    def set_test_default(self):
        self.configure(red=125, green=0, blue=125, white=0, brightness=255)
        self.on()