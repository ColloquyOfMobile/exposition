from colloquy.base_thread import BaseThread
from time import time, sleep
from .html import HTML


class TurnBackAndForthAroundF1(BaseThread):
    def __init__(self, owner):
        super().__init__(owner=owner)
        self._html = HTML(owner=self)

        self[self.html.name] = self.html.handle_request
        self._position_memory = None
        self._motion_range = 3000

    @property
    def html(self):
        return self._html

    @property
    def name(self):
        return "turn back and forth around f1"

    @property
    def origin(self):
        return self.owner.male1_in_front_of_f1

    def loop(self):
        if not self.owner.is_moving:
            self.toggle_position()

    def setup(self):
        pass

    def setdown(self):
        pass

    # def snapshot(self, path):
    # states = super().snapshot(path=path)
    # _path = states["path"]
    # return states

    def toggle_position(self):
        if self._position_memory is None:
            self.turn_to_max_position()
            return

        if self._position_memory == "max":
            self.turn_to_min_position()
            return

        if self._position_memory == "min":
            self.turn_to_max_position()
            return

    def turn_to_max_position(self):
        value = self.origin + self._motion_range // 2
        self.owner.dxl.goal_position.write(value)
        self._position_memory = "max"

    def turn_to_min_position(self):
        value = self.origin - self._motion_range // 2
        self.owner.dxl.goal_position.write(value)
        self._position_memory = "min"

    @property
    def snapshot_children(self):
        children = {}
        return children
