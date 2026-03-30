# from colloquy.wsgi.root.body.action_item import ActionItem
import traceback
from colloquy.base import Base
from pathlib import Path
import traceback

from .html import HTML
from .test1 import Test1

class Tests(Base):

    def __init__(self, owner):
        super().__init__(owner)
        # self.opened = None

        self._html = HTML(owner=self)
        self._test1 = Test1(owner=self)
        self._hardware = self.owner.hardware

        self[self.html.name] = self.html.handle_request
        self.add(self.test1)

        self._threaded_tests = {self.test1}

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
    def colloquy(self):
        return self.owner.colloquy

    @property
    def test1(self):
        return self._test1

    @property
    def html(self):
        return self._html

    @property
    def name(self):
        return "tests"

    @property
    def workspace(self):
        return self

    @property
    def hardware(self):
        return self._hardware

    def stop(self):
        for test in self._threaded_tests:
            test.stop()