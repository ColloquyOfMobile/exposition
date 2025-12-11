from utils import CustomDoc
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

    def html(self):
        doc, tag, text = CustomDoc().tagtext()
        label = "toggle LEDs on"
        if self.owner.state:
            label = "toggle LEDs off"
        with tag("div", style="margin-bottom: 1rem;"):
            with tag("a", href=f"/{self.path.as_posix()}"):
                text(label)

        return doc.getvalue()