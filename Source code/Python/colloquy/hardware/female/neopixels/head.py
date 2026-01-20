from colloquy.hardware.neopixel import Neopixel
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