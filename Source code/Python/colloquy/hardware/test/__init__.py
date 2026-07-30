from colloquy.base import Base
from pathlib import Path
from .html import HTML


class Test(Base):
    def __init__(self, owner):
        super().__init__(owner)

    def __call__(self, request):
        request = Path(request)
        if not request.parts:
            raise NotImplementedError

        key, *leftover = request.parts

        if key in self:
            self[key](request="/".join(leftover))
            return

        raise NotImplementedError(f"{key=}, {leftover=}, in {self=}")

    @property
    def html(self):
        return self._html

    @property
    def name(self):
        return "test"

    @property
    def colloquy(self):
        return self.owner.colloquy
