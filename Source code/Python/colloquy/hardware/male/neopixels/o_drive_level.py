from colloquy.hardware.neopixel import Neopixel
from colloquy.base import Base

from pathlib import Path
from threading import Event


class ODriveLevel(Neopixel):
    def __init__(self, owner):
        super().__init__(owner=owner, name="o drive level")
        self._body = owner
        self.color = self.orange

    @property
    def male(self):
        return self.owner.male

    @property
    def arduino_path(self):
        return Path(f"m{self.male.id_number}/{self.name}")

    def set_test_default(self):
        self.configure(red=0, green=0, blue=255, white=0, brightness=255)
        self.on()
