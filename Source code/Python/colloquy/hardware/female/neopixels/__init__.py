from colloquy.base import Base

from pathlib import Path
from .html import HTML

from .head import Head
from .feet import Feet
from .body_o import BodyO
from .body_p import BodyP

class Neopixels(Base):
    def __init__(self, owner):
        super().__init__(owner=owner)
        self._html = HTML(owner=self)
        self._arduino = owner.arduino

        self._head = Head(owner=self)
        self._body_o = BodyO(owner=self)
        self._body_p = BodyP(owner=self)
        self._feet = Feet(owner=self)

        self[self.html.name] = self.html.handle_request
        self[self.head.name] = self.head
        self[self.body_o.name] = self.body_o
        self[self.body_p.name] = self.body_p
        self[self.feet.name] = self.feet

    def __iter__(self):
        yield self.head
        yield self.body_o
        yield self.body_p
        yield self.feet

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def html(self):
        return self._html

    @property
    def arduino(self):
        return self._arduino

    @property
    def name(self):
        return "neopixels"

    @property
    def head(self):
        return self._head

    @property
    def body_o(self):
        return self._body_o

    @property
    def body_p(self):
        return self._body_p

    @property
    def feet(self):
        return self._feet

    @property
    def snapshot_children(self):
        children = {}
        children.update(
            {
                "head": self.head,
                self.body_o.name: self.body_o,
                self.body_p.name: self.body_p,
                "feet": self.feet,
            }
        )
        return children
