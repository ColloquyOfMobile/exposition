# from colloquy.wsgi.root.body.action_item import ActionItem
from colloquy.wsgi.root.body.workspace.item import Item, Action
from colloquy.wsgi.root.body.command import Command, HTML as _HTML


class ToggleOnOff(Command):
    
    def __init__(self, owner):
        Command.__init__(self, owner)
        self._action = Action(owner=self)
        self._html = HTML(owner=self)
    
    def __call__(self):
        self.owner.toggle()

    @property
    def name(self):
        return "toggle on-off"

class HTML(_HTML):

    def __call__(self):
        doc, tag, text = self.doc.tagtext()
        label = "on"
        if self.owner.owner.state:
            label = "off"
        with tag("form", method="post", style="display: flex; "):
            with tag("button", name="action", value=self.owner.action.value):
                text(label)