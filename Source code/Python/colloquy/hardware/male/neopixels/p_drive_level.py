from colloquy.hardware.neopixel import Neopixel
from colloquy.base import Base

from pathlib import Path
from threading import Event


class PDriveLevel(Neopixel):
    def __init__(self, owner):
        super().__init__(owner=owner, name="p drive level")
        self._body = owner
        self.color = self.puce

    def set_test_default(self):
        self.configure(red=0, green=255, blue=0, white=0, brightness=255)

    @property
    def male(self):
        return self.owner.male

    @property
    def arduino_path(self):
        return Path(f"m{self.male.id_number}/{self.name}")
