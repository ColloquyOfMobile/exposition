from colloquy.wsgi.root.body.action_item import ActionItem
from colloquy.wsgi.root.body.command import Command, HTML as _HTML


class Restart(Command):
    
    def __init__(self, owner):
        Command.__init__(self, owner)
        self._action = Action(owner=self)
        self._html = HTML(owner=self)

    @property
    def name(self):
        return "restart"

class Action(ActionItem):

    def __call__(self):
        self.owner.events.shutdown.set()
        self.owner.events.restart.set()
        self.owner.open()
        
        


class HTML(_HTML):
    
    def _call_is_opened(self): 
        doc, tag, text = self.doc.tagtext()                 
        with tag("div"):
            with tag("div"):
                text("Restarting...")
            with tag("div"):
                with tag("a", href=""):
                    text("Click here to see the changes.")