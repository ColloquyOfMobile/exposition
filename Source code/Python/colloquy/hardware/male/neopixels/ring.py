from colloquy.hardware.neopixel import Neopixel
from colloquy.base import Base

from pathlib import Path
from threading import Event

class Ring(Neopixel):

    def __init__(self, owner):
        super().__init__(owner=owner, name="ring")
        self._body = owner
        self.white.value = 255
        self.brightness.value = 100
    
    @property
    def male(self):
        return self.owner.owner

    @property
    def arduino_path(self):
        return Path(f"m{self.male.id_number}/{self.name}")

    def set_test_default(self):
        self.configure(red=125, green=125, blue=0, white=0, brightness=255)
        self.on()