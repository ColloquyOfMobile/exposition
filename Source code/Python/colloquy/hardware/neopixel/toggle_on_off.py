# from colloquy.wsgi.root.body.action_item import ActionItem
# from colloquy.wsgi.root.body.workspace.item import Item, Action
# from colloquy.wsgi.root.body.command import Command, HTML as _HTML
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
        label = "on"
        if self.owner.state:
            label = "off"
        with tag("div"):
            with tag("a", href=f"/{self.path.as_posix()}"):
                text(label)
        
        return doc.getvalue()

# class HTML(_HTML):

    # def __call__(self):
        # doc, tag, text = self.doc.tagtext()
        # label = "on"
        # if self.owner.owner.state:
            # label = "off"
        # with tag("form", method="post", style="display: flex; "):
            # with tag("button", name="action", value=self.owner.action.value):
                # text(label)