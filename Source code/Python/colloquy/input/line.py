# -*- coding: utf-8 -*-
# project2/my_server/solution1/input/line.py

from colloquy.base import Base


class Line(Base):
    def __init__(self, owner, name, keys):
        super().__init__(owner=owner, name=name)
        self._keys = keys

    @property
    def keys(self):
        return self._keys
