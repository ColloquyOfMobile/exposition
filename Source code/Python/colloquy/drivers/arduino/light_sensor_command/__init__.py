# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/dxl/__init__.py

from colloquy.base import Base
from colloquy.input import Input


class LightSensorCommand(Base):
    def __init__(self, owner, arduino_path):
        self._name = arduino_path
        super().__init__(owner=owner)

        # if not self.is_readonly():
        self._input = Input(owner=self)
        self[self.input.name] = self.input

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
    def name(self):
        return self._name

    @property
    def dxl_id(self):
        return self.owner.dxl_id

    def is_readonly(self):
        return self._write_func is None

    def commit(self, value):
        value = int(value)
        return self.write(value=value)

    def read(self, request=None):
        return self._read_func(self.dxl_id, self._register)

    def write(self, value):
        if self._write_func is None:
            raise NotImplementedError(self)
        return self._write_func(self.dxl_id, self._register, value)
