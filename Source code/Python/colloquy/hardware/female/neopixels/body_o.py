from colloquy.hardware.neopixel import Neopixel
from colloquy.base import Base

from pathlib import Path
from threading import Event


class BodyO(Neopixel):
    def __init__(self, owner):
        super().__init__(owner=owner, name="bodyO")
        self._body = owner
        self.color = self.orange

    @property
    def female(self):
        return self.owner.owner

    @property
    def arduino_path(self):
        return Path(f"f{self.female.id_number}/{self.name}")

    def set_test_default(self):
        self.configure(red=125, green=125, blue=0, white=0, brightness=255)
        self.on()
