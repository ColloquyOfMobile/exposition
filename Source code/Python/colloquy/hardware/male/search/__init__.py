from colloquy.base_thread import BaseThread
from time import time, sleep
from .html import HTML
from .blink import Blink


class Search(BaseThread):
    def __init__(self, owner):
        super().__init__(owner=owner)
        self._html = HTML(owner=self)
        self._blink = Blink(owner=self)

        self[self.html.name] = self.html.handle_request
        self[self.blink.name] = self.blink

    @property
    def male(self):
        return self.owner

    @property
    def html(self):
        return self._html

    @property
    def blink(self):
        return self._blink

    @property
    def name(self):
        return "search"

    def loop(self):
        if not self.owner.is_moving:
            self.owner.toggle_position()

    def setup(self):
        self.blink.start(started_by=self)
        pass

    def setdown(self):
        print(f"Set down {self=}")
        pass

    # def snapshot(self, path):
    # states = {
    # "path": path + (self.name, ),
    # "name": self.name,
    # "close": self.close,
    # "open": self.open,
    # "opened": self._is_opened,
    # }
    # return states

    @property
    def snapshot_children(self):
        children = {}
        return children
