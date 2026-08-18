from colloquy.base_thread import BaseThread
from time import time, sleep


class TurnBackAndForthAroundF1(BaseThread):
    def __init__(self, owner):
        super().__init__(owner=owner)

        self._position_memory = None
        # In degrees of the bar: the 3000 servo units this used to swing
        # through the bar's 1:3 reduction.
        self._sweep = 87.891

    @property
    def name(self):
        return "turn back and forth around f1"

    @property
    def origin(self):
        """The angle it swings around: where male1 faces female1."""
        return self.owner.meeting_angle("male1", "female1")

    def loop(self):
        if not self.owner.is_moving:
            self.toggle_position()

    def setup(self):
        pass

    def setdown(self):
        pass

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
        self.owner.turn_to(self.origin + self._sweep / 2)
        self._position_memory = "max"

    def turn_to_min_position(self):
        self.owner.turn_to(self.origin - self._sweep / 2)
        self._position_memory = "min"

    @property
    def snapshot_children(self):
        children = {}
        return children
