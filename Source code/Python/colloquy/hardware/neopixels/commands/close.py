from colloquy.base import Base
# from colloquy.wsgi.root.body.command import Command, HTML as _HTML


class Close(Base):
    def __init__(self, owner):
        super().__init__(owner)
        self._action = Action(owner=self)
        self._html = HTML(owner=self)

    def __call__(self):
        self.owner.hardware.opened = None

    @property
    def name(self):
        return "close"
