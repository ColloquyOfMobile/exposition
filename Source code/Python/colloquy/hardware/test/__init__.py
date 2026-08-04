from colloquy.base import Base
from pathlib import Path
from .html import HTML

class Test(Base):
    def __init__(self, owner):
        super().__init__(owner)

    @property
    def html(self):
        return self._html

    @property
    def name(self):
        return "test"

    @property
    def colloquy(self):
        return self.owner.colloquy
