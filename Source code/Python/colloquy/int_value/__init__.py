# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/dxl/__init__.py
from pathlib import Path
from dynamixel_sdk import (
    PortHandler,
    PacketHandler,
    COMM_SUCCESS,
)  # Uses Dynamixel SDK library

from colloquy.base import Base
from time import time, sleep
from colloquy.input import Input


class IntValue(Base):
    def __init__(self, owner, name, getter, setter=None):
        self._name = name
        super().__init__(owner=owner)
        self._getter = getter
        self._setter = setter

        self["get"] = self.get

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
    def name(self):
        return self._name

    def is_readonly(self):
        return self._setter is None

    def commit(self, value):
        value = int(value)
        return self.set(value=value)

    def get(self, request=None):
        return self._getter()

    def set(self, value):
        if self._setter is None:
            raise NotImplementedError(self)
        return self._setter(value)
