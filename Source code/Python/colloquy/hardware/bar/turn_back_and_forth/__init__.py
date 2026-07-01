from colloquy.base_thread import BaseThread
from time import time, sleep
from .html import HTML

class TurnBackAndForth(BaseThread):

    def __init__(self, owner):
        super().__init__(owner=owner)

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
    
    def snapshot(self, path):
        states = super().snapshot(path=path)
        _path = states["path"]
        return states