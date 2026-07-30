from colloquy.base_thread import BaseThread
from time import time, sleep
from .html import HTML


class TurnBackAndForth(BaseThread):
    def __init__(self, owner):
        super().__init__(owner=owner)
        self._html = HTML(owner=self)

        self[self.html.name] = self.html.handle_request

    @property
    def html(self):
        return self._html

    @property
    def name(self):
        return "turn back and forth"

    def loop(self):
        if not self.owner.is_moving:
            self.owner.toggle_position()

    def setup(self):
        pass

    def setdown(self):
        pass

    @property
    def snapshot_children(self):
        children = {}
        return children
