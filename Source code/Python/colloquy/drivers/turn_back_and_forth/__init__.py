from colloquy.base_thread import BaseThread


class TurnBackAndForth(BaseThread):
    # Started by hand from the page rather than by any appetite, which
    # is the whole point of it: it is how a body is watched moving with
    # nothing else going on.
    scenario_names = ("swaying-a-body-by-hand",)

    def __init__(self, owner):
        super().__init__(owner=owner)

    @property
    def name(self):
        return f"turn back and forth {self.owner.name}"

    def loop(self):
        if not self.owner.is_moving:
            self.owner.toggle_position()

    def setup(self):
        pass

    def setdown(self):
        pass

    @property
    def snapshot_children(self):
        return self._with_scenarios({})
