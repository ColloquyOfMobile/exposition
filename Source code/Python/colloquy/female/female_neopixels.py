from colloquy.neopixel import Neopixel
from pathlib import Path
from threading import Event



class HeadFemaleNeopixel(Neopixel):

    def __init__(self, owner):
        Neopixel.__init__(self, owner=owner, name="head neopixel")
    
    def set_test_default(self):
        self.configure(red=0, green=255, blue=0, white=0, brightness=255)
        self.on()


class BodyFemaleNeopixel(Neopixel):

    def __init__(self, owner):
        Neopixel.__init__(self, owner=owner, name="body neopixel")  
    
    def set_test_default(self):
        self.configure(red=255, green=0, blue=0, white=0, brightness=255)
        self.on()


class FeetFemaleNeopixel(Neopixel):

    def __init__(self, owner):
        Neopixel.__init__(self, owner=owner, name="feet neopixel")  
    
    def set_test_default(self):
        self.configure(red=0, green=0, blue=255, white=0, brightness=255)
        self.on()