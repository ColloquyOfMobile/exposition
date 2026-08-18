# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/dxl/__init__.py
from ..register_handler import RegisterHanlder


class GoalPosition(RegisterHanlder):
    def __init__(
        self,
        owner,
    ):
        super().__init__(
            owner=owner,
            name="goal position",
            register=116,
            read_func=owner.u2d2.read_4_bytes,
            write_func=owner.u2d2.write_4_bytes,
            # Same as the position register: a goal below the servo's zero
            # is written as two's complement and read back unsigned.
            signed=True,
        )

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
