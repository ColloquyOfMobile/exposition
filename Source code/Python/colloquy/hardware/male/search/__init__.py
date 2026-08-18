from colloquy.base_thread import BaseThread
from .blink import Blink


class Search(BaseThread):
    def __init__(self, owner):
        super().__init__(owner=owner)
        self._blink = Blink(owner=self)

        self[self.blink.name] = self.blink

    @property
    def male(self):
        return self.owner

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

    @property
    def snapshot_children(self):
        children = {}
        return children
