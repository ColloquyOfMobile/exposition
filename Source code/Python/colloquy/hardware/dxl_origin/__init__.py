# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/dxl/__init__.py
from colloquy.base import Base
from colloquy.input import Input
from colloquy.hardware.value_setter2 import ValueSetter2


class DXLOrigin(Base):
    def __init__(self, owner):
        super().__init__(owner=owner)

        self["get"] = self.get
        # An origin is a raw servo reading: negative on a body whose zero
        # sits below the servo's, and up to five figures on the bar. The
        # setter it had could only reach 0 to 100, on a quantity that runs
        # past 10000 - so the page could not express most of the values
        # this node exists to hold. (Calibration is normally "set current
        # position as dxl origin" on the body itself; this is for typing a
        # number in by hand.)
        self._setter = ValueSetter2(
            owner=self,
            min_value=-20000,
            max_value=20001,
            set_func=self.set,
            get_func=self.get,
        )

        # if not self.is_readonly():
        self._input = Input(owner=self)
        self[self.input.name] = self.input

    @property
    def input(self):
        return self._input

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def params(self):
        return self.colloquy.params

    @property
    def name(self):
        return "dxl origin"

    @property
    def female(self):
        return self.owner

    @property
    def setter(self):
        return self._setter

    @property
    def dxl_origin(self):
        return self

    def is_readonly(self):
        return False

    def commit(self, value):
        value = int(value)
        return self.set(value=value)

    def get(self, request=None):
        return self.params[self.owner.name][self.name]

    def set(self, value):
        self.params[self.owner.name][self.name] = value

    @property
    def snapshot_children(self):
        children = {}
        children.update(
            {
                self.setter.name: self.setter,
            }
        )
        return children

    def _snapshot_if_opened(self, path):
        # "value" was a bare int in snapshot_children, which Base._snapshot_
        # if_opened's default walk crashes on the instant this node is
        # opened directly (calls .snapshot_as_child() on it, which an int
        # doesn't have) - reachable on every body's own "dxl origin" node.
        states = super()._snapshot_if_opened(path)
        states["value"] = {
            "path": path + ("value",),
            "name": "value",
            "value": self.get(),
        }
        return states

