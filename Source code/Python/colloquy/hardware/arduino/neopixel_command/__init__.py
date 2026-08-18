# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/dxl/__init__.py
from pathlib import Path

from colloquy.base import Base
from .value_setter import ValueSetter


class NeopixelCommand(Base):
    def __init__(self, owner, arduino_path):
        self._name = arduino_path.replace("/", "_")
        self._arduino_path = Path(arduino_path)
        super().__init__(owner=owner)

        self._value_setters = [
            ValueSetter(owner=self, name="r"),
            ValueSetter(owner=self, name="g"),
            ValueSetter(owner=self, name="b"),
            ValueSetter(owner=self, name="w"),
        ]

        for setter in self._value_setters:
            self[setter.name] = setter

        self["send"] = self._send

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
