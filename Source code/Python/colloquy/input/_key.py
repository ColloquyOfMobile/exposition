# -*- coding: utf-8 -*-
# project2/my_server/solution1/input/key.py

from my_server.debug import Debug


class Key(Debug):
    def __init__(self, owner, name):
        super().__init__(owner=owner, name=name)
        # self._html = HTML(owner=self)

    def __call__(self):
        self.input.value += self.name
        return self.owner.owner  # Too much responsibility. Opening state should handle in OpenedClasses separatly

    @property
    def input(self):
        return self.owner.input
