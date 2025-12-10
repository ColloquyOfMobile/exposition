from colloquy.base import Base
from pathlib import Path
from utils import CustomDoc
from .increment import Increment


class Brightness(Base):

    def __init__(self, owner, name):
        Base.__init__(self, owner)
        self._name = name
        self._value = 0

        self._neopixel = owner

        self._increment1 = Increment(owner=self, multiplier=1)
        self._increment10 = Increment(owner=self, multiplier=10)
        self._increment100 = Increment(owner=self, multiplier=100)

        self[self._increment1.name] = self._increment1
        self[self._increment10.name] = self._increment10
        self[self._increment100.name] = self._increment100


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
    def neopixel(self):
        return self._neopixel

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self.set_without_updating(value)
        self.neopixel.update()

    def set_without_updating(self, value):
        if value > 100:
            value = 100
        if value < 0:
            value = 0
        self._value = value


    def html(self):
        doc, tag, text = CustomDoc().tagtext()

        with tag("div", style="display:flex; flex-direction: column; margin-bottom: 1rem;"):
            with tag("div", style="margin-bottom: 0.5rem;"):
                text(f"{self.name} = {self.value:03} %")

            with tag("div", style="display:flex;"):

                for command in self:
                    doc.asis(self[command].html())

        return doc.getvalue()