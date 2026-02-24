from .neopixels import Neopixels # Head, BodyO, BodyP, Feet
from .drives import Drives
from pathlib import Path
from colloquy.base_thread import BaseThread
from .search import Search
from .html import HTML
from .test import Test


class Female(BaseThread):

    def __init__(self, owner, id_number):
        self._name = f"female{id_number}"
        self._id_number = id_number
        super().__init__(owner=owner)
        self._dxl = owner.u2d2.dxls[self.name]
        self._html = HTML(owner=self)
        self._arduino = owner.arduino

        self._drives = Drives(owner=self)
        self._search = Search(owner=self)

        self._neopixels = Neopixels(owner=self)
        self._test = Test(owner=self)

        self[self.html.name] = self.html.handle_request
        self[self.neopixels.name] = self.neopixels
        self[self.drives.name] = self.drives
        self[self.test.name] = self.test
        self[self.search.name] = self.search

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
    def dxl(self):
        return self._dxl

    @property
    def test(self):
        return self._test

    @property
    def search(self):
        return self._search

    @property
    def drives(self):
        return self._drives

    @property
    def id_number(self):
        return self._id_number

    @property
    def female(self):
        return self

    @property
    def html(self):
        return self._html

    @property
    def arduino(self):
        return self._arduino

    @property
    def name(self):
        return self._name

    @property
    def neopixels(self):
        return self._neopixels

    @property
    def is_moving(self):
        return self.dxl.is_moving

    def loop(self):
        pass

    def setup(self):
        self.dxl.init_hardware()
        self.drives.start(started_by=self)

    def setdown(self):
        self.drives.stop()
        self.search.stop()