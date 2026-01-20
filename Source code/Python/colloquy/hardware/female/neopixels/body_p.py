from colloquy.hardware.neopixel import Neopixel
from colloquy.base import Base

from pathlib import Path
from threading import Event

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