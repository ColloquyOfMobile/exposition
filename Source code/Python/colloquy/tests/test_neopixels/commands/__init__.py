from colloquy.base import Base

from .close import Close

class Commands(Base):
    def __init__(self, owner):
        super().__init__(owner)
        self._close = Close(owner=self)

    @property
    def tests(self):
        return self.owner.tests

    @property
    def close(self):
        return self._close

    @property
    def name(self):
        return "command"
