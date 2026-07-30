from pathlib import Path
from colloquy.base import Base
from .html import HTML


class Test(Base):
    def __init__(self, owner):
        super().__init__(owner=owner)
        self._html = HTML(owner=self)

        self[self.html.name] = self.html.handle_request

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
    def name(self):
        return "test"

    @property
    def html(self):
        return self._html

    @property
    def colloquy(self):
        return self.owner.colloquy
