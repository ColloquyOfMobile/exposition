from colloquy.base_thread import BaseThread


class Search(BaseThread):
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
        children = {}
        return children
