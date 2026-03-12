# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/dxl/__init__.py
from pathlib import Path
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS  # Uses Dynamixel SDK library
from utils import CustomDoc
from colloquy.base import Base
from .html import HTML
from time import time, sleep
from colloquy.input import Input
from .value_setter import ValueSetter

class NeopixelCommand(Base):
    def __init__(self, owner, arduino_path):
        self._name = arduino_path.replace("/", "_")
        self._arduino_path = Path(arduino_path)
        super().__init__(owner=owner)
        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request
        
        self._value_setters = [
            ValueSetter(owner=self, name="r"),
            ValueSetter(owner=self, name="g"),
            ValueSetter(owner=self, name="b"),
            ValueSetter(owner=self, name="w"),
        ]
        
        for setter in self._value_setters:
            self[setter.name] = setter
        
        self["send"] = self._send

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
    def value_setters(self):
        return self._value_setters
    
    @property
    def input(self):
        return self._input
    
    @property
    def arduino(self):
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
    
    def _send(self, request=None):
        data = {
            "r": self._value_setters[0].value,
            "g": self._value_setters[1].value,
            "b": self._value_setters[2].value,
            "w": self._value_setters[3].value,
        }
        self.arduino.send(path=self._arduino_path, **data)
        