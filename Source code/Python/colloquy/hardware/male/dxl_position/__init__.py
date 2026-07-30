# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/dxl/__init__.py
from pathlib import Path
from dynamixel_sdk import (
    PortHandler,
    PacketHandler,
    COMM_SUCCESS,
)  # Uses Dynamixel SDK library

from colloquy.base import Base
from .html import HTML
from time import time, sleep
from colloquy.input import Input


class DXLPosition(Base):
    def __init__(self, owner):
        super().__init__(owner=owner)

        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request

        self["get"] = self.get

        # if not self.is_readonly():
        self._input = Input(owner=self)
        self[self.input.name] = self.input

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
    def input(self):
        return self._input

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def params(self):
        return self.colloquy.params

    @property
    def html(self):
        return self._html

    @property
    def name(self):
        return "position"

    @property
    def female(self):
        return self.owner

    def is_readonly(self):
        return False

    def commit(self, value):
        value = int(value)
        return self.set(value=value)

    def get(self, request=None):
        return self.owner.dxl.position.read()

    def set(self, value):
        self.params[self.owner.name][self.name] = value
