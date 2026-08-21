from colloquy.drivers.neopixel import Neopixel

from pathlib import Path


class UpRing(Neopixel):
    def __init__(self, owner):
        super().__init__(owner=owner, name="up ring")
        self._body = owner
        self.white.value = 255

    @property
    def male(self):
        return self.owner.male

    @property
    def arduino_path(self):
        return Path(f"m{self.male.id_number}/{self.name}")

    def set_test_default(self):
        self.configure(red=0, green=0, blue=255, white=0, brightness=255)
        self.on()
