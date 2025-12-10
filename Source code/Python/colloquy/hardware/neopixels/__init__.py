from pathlib import Path
from colloquy.base import Base
from .commands import Commands



class Neopixels(Base):

    def __init__(self, owner):
        super().__init__(owner=owner, name="neopixels")
        self._commands = Commands(owner=self)

    def __iter__(self):
        neopixels = []
        for body in self.owner.bodies:
            neopixels.extend(body.neopixels)
        yield from neopixels