# -*- coding: utf-8 -*-
# project2/my_server/solution1/input/__init__.py

from colloquy.base import Base


class Input(Base):
    """A value being typed in, one character at a time.

    What is left of the on-screen keyboard reverted in 9428194. Five
    nodes still build one - a drive, a register, a dxl origin, a light
    sensor command, a neopixel value setter - and register it under
    their own "input" key, but nothing draws it: Input answers no
    snapshot_children, so the page cannot walk to it. Its own siblings
    (Line, Erase, Key) and the members that used them went with the
    revert; only this remains, and it is a candidate for going too.
    """
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
    def input(self):
        return self

    @property
    def name(self):
        return "input"
