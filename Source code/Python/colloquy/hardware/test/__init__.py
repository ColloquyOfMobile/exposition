from colloquy.base import Base
from pathlib import Path
from .html import HTML


class Test(Base):

    def __init__(self, owner):
        super().__init__(owner)
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
    def html(self):
        return self._html

    @property
    def name(self):
        return "test"

    @property
    def colloquy(self):
        return self.owner.colloquy

    # @property
    # def opened(self):
        # return self._opened

    # @opened.setter
    # def opened(self, value):
        # # Value is None only in a Close(), this is to avoid recursion.
        # if value is not None:
            # if self._opened is not None:
                # self._opened.close()

        # self._opened = value

    # @property
    # def drives(self):
        # return self._drives

    # @property
    # def arduino(self):
        # return self._arduino

    # @property
    # def u2d2(self):
        # return self._u2d2

    # @property
    # def bar(self):
        # return self._bar

    # @property
    # def mirrors(self):
        # return self._mirrors

    # @property
    # def males(self):
        # return self._males

    # @property
    # def speakers(self):
        # return self._speakers

    # @property
    # def females(self):
        # return self._females

    # @property
    # def female1(self):
        # return self._female1

    # @property
    # def female2(self):
        # return self._female2

    # @property
    # def female3(self):
        # return self._female3

    # @property
    # def moving_elements(self):
        # return self._moving_elements

    # @property
    # def neopixels(self):
        # neopixels = []
        # for body in self.bodies:
            # neopixels.extend(body.neopixels)
        # return neopixels

    # @property
    # def bodies(self):
        # bodies = []
        # for body in self.females:
            # bodies.append(body)
        # for body in self.males:
            # bodies.append(body)
        # return bodies

    # def loop(self):
        # pass

    # def setup(self):
        # for bodies in self.hardware.bodies:
            # bodies.start(started_by=self)

    # def setdown(self):
        # for bodies in self.hardware.bodies:
            # bodies.stop()