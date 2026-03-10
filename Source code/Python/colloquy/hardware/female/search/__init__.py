from colloquy.base_thread import BaseThread
from time import time, sleep
from .html import HTML
from .read_pattern import ReadPattern

class Search(BaseThread):

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._html = HTML(owner=self)
        self._read_pattern = None

        self[self.html.name] = self.html.handle_request
        self[self.read_pattern.name] = self.read_pattern

    @property
    def html(self):
        return self._html

    @property
    def name(self):
        return "search"

    @property
    def read_pattern(self):
        if self._read_pattern is None:
            self._read_pattern = ReadPattern(owner=self)
        return self._read_pattern

    def loop(self):
        if not self.owner.is_moving:
            self.owner.toggle_position()

    def setup(self):
        self.owner.read_pattern.start(started_by=self)
        pass

    def setdown(self):
        print(f"Set down {self=}")        
        pass