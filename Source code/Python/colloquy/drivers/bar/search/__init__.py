from colloquy.base_thread import BaseThread


class Search(BaseThread):
    # End-to-end travel, and the one pair it never brings together.
    scenario_names = ("bar-wandering",)

    def __init__(self, owner):
        super().__init__(owner=owner)

    @property
    def name(self):
        return "search"

    def loop(self):
        if not self.owner.is_moving:
            self.owner.toggle_position()

    def setup(self):
        pass

    def setdown(self):
        print(f"Set down {self=}")
        pass

    @property
    def snapshot_children(self):
        return self._with_scenarios({})
