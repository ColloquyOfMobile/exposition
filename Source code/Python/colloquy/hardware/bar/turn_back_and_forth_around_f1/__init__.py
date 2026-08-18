from colloquy.base_thread import BaseThread


class TurnBackAndForthAroundF1(BaseThread):
    def __init__(self, owner):
        super().__init__(owner=owner)

        self._position_memory = None

    @property
    def name(self):
        return "turn back and forth around f1"

    @property
    def origin(self):
        """The angle it swings around: where male1 faces female1."""
        return self.owner.meeting_angle("male1", "female1")

    @property
    def sweep(self):
        """How far it swings around that pair, end to end, in degrees of
        the bar - a narrower range than its full travel, which is the
        point of this behaviour. 87.891 is the 3000 servo units it used to
        swing, through the 1:3 reduction."""
        return self.owner.params["bar"]["motion range around female1"]

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
        self.owner.turn_to(self.origin + self.sweep / 2)
        self._position_memory = "max"

    def turn_to_min_position(self):
        self.owner.turn_to(self.origin - self.sweep / 2)
        self._position_memory = "min"

    @property
    def snapshot_children(self):
        children = {}
        return children
