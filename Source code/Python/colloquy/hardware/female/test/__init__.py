from pathlib import Path
from colloquy.base import Base
from .html import HTML

class Test(Base):
    def __init__(self, owner):
        super().__init__(owner=owner)
        self._html = HTML(owner=self)

        self[self.html.name] = self.html.handle_request

    @property
    def name(self):
        return "test"

    @property
    def html(self):
        return self._html

    @property
    def colloquy(self):
        return self.owner.colloquy
