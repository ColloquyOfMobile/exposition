# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/dxl/__init__.py
from pathlib import Path
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS  # Uses Dynamixel SDK library
from utils import CustomDoc
from colloquy.base import Base
from .html import HTML
from time import time, sleep
from colloquy.input import Input

class ValueSetter(Base):
    def __init__(self, owner, name):
        self._name = name
        super().__init__(owner=owner)
        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request
        
        self._value = 255
        
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
    def dxl(self):
        return self.owner

    @property
    def u2d2(self):
        return self.owner.u2d2

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def html(self):
        return self._html

    @property
    def name(self):
        return self._name

    @property
    def dxl_id(self):
        return self.owner.dxl_id

    @property
    def value(self):
        return self._value
        
    def commit(self, value):
        self._value = int(value)
        # return self.write(value=value)