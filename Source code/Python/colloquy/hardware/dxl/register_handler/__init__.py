# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/dxl/__init__.py
from pathlib import Path

from colloquy.base import Base
from .html import HTML
from time import time, sleep
from colloquy.input import Input

from colloquy.hardware.value_setter2 import ValueSetter2

class RegisterHanlder(Base):
    def __init__(
        self,
        owner,
        name,
        register,
        read_func,
        write_func=None,
        open_in=None,
        html_class=None,
    ):

        self._name = name
        super().__init__(owner=owner)
        self._read_func = read_func
        self._write_func = write_func
        self._register = register

        if write_func is not None:
            self._setter = ValueSetter2(
                owner=self, min_value=-5000, max_value=5000, set_func=self.write
            )

        if html_class is None:
            self._html = HTML(owner=self)
        else:
            self._html = html_class(owner=self)
        self[self.html.name] = self.html.handle_request

        self["read"] = self.read

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
    def html(self):
        return self._html

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

    # def snapshot(self, path):
    # states = super().snapshot(path=path)
    # _path = states["path"]
    # states["value"]  = self.read()

    # if not self.is_readonly():
    # states[self._setter.name] = self._setter.snapshot(_path)

    # return states

    @property
    def snapshot_children(self):
        children = {}

        if not self.is_readonly():
            children[self._setter.name] = self._setter

        return children

    def _snapshot_if_opened(self, path):
        # "value" was a bare int in snapshot_children, which Base._snapshot_
        # if_opened's default walk crashes on the instant this node is
        # opened directly (calls .snapshot_as_child() on it, which an int
        # doesn't have). This is the base class for every DXL register
        # (temperature/position/torque_enabled/goal_position/...) on every
        # servo, so this was reachable at ~72 distinct nodes app-wide.
        states = super()._snapshot_if_opened(path)
        states["value"] = {
            "path": path + ("value",),
            "name": "value",
            "value": self.read(),
        }
        return states
