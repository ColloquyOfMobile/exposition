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
from colloquy.hardware.value_setter import ValueSetter

class DXLOrigin(Base):
    def __init__(self, owner):
        super().__init__(owner=owner)

        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request

        self["get"] = self.get
        self._setter = ValueSetter(owner=self, limit=101)

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
    def html(self):
        return self._html

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

