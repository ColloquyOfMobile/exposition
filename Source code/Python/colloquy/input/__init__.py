# -*- coding: utf-8 -*-
# project2/my_server/solution1/input/__init__.py

import string
from colloquy.base import Base


from .line import Line

# from .key import Key
from .erase import Erase


class Input(Base):
    def __init__(self, owner):
        super().__init__(owner=owner)
        self.value = "0"

    def __call__(self, request):
        if request == "erase":
            self.value = self.value[:-1]
            if not self.value:
                self.value = "0"
            return
        if request == "commit":
            self.owner.commit(self.value)
            self.value = "0"
            return
        if self.value == "0":
            self.value = request
            return
        self.value += request
        # raise NotImplementedError

    @property
    def memory(self):
        return self.owner.memory

    @property
    def commands(self):
        commands = {}
        for name in "1234567890" + string.ascii_lowercase + "_'\"<>-":
            commands[name] = Key(owner=self, name=name)

        commands[f"{self.value=}"] = None

        return commands

    @property
    def lines(self):
        return self._lines

    @property
    def input(self):
        return self

    @property
    def name(self):
        return "input"

    @property
    def erase(self):
        return Erase(owner=self)

    @property
    def space(self):
        return Space(owner=self)
