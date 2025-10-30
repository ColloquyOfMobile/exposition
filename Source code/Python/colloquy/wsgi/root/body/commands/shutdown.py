from colloquy.wsgi.root.body.action_item import ActionItem
from colloquy.wsgi.root.body.command import Command, HTML as _HTML

class Shutdown(Command):
    
    def __init__(self, owner):
        Command.__init__(self, owner)
        self._action = Action(owner=self)
        self._html = HTML(owner=self)

    @property
    def name(self):
        return "shutdown"

class Action(ActionItem):

    def __call__(self):
        self.owner.events.shutdown.set()
        self.owner.open()
        
        


class HTML(_HTML):
    
    def _call_is_opened(self):    
        doc, tag, text = self.doc.tagtext()                   
        with tag("div"):
            text("Goodbye !")