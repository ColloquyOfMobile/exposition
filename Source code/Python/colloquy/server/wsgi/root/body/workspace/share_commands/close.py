# from colloquy.wsgi.root.body.action_item import ActionItem
# from colloquy.wsgi.root.body.command import Command, HTML
from colloquy.base import Base


class Close(Base):
    
    def __init__(self, owner):
        super().__init__(owner)
        # self._action = Action(owner=self)
        # self._html = HTML(owner=self)
    
    def __call__(self):
        self.owner.opened = None

    @property
    def name(self):
        return "close"

# class Action(ActionItem):

    # def __call__(self):
        # self.owner()
        
        

    # def _call_is_opened(self): 
        # doc, tag, text = self.doc.tagtext()                 
        # with tag("div"):
            # with tag("div"):
                # text("Restarting...")
            # with tag("div"):
                # with tag("a", href=""):
                    # text("Click here to see the changes.")