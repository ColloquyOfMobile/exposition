from colloquy.base import Base
from pathlib import Path


class Test(Base):
    def __init__(self, owner):
        super().__init__(owner)

    @property
    def name(self):
        return "test"

    @property
    def colloquy(self):
        return self.owner.colloquy
