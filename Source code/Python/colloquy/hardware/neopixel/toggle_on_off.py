from colloquy.base import Base


class ToggleOnOff(Base):
    def __init__(self, owner):
        super().__init__(owner=owner)
        # self._action = Action(owner=self)
        # self._html = HTML(owner=self)

    def __call__(self, request):
        self.owner.toggle()

    @property
    def name(self):
        return "toggle on-off"
