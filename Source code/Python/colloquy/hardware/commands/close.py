from colloquy.base import Base


class Close(Base):
    def __init__(self, owner):
        super().__init__(owner)

    def __call__(self):
        self.owner.workspace.opened = None

    @property
    def name(self):
        return "close"
