from colloquy.wsgi.root.body.item import Item
from .html import HTML
from .close import Close

class Commands(Item):
    
    def __init__(self, owner):
        Item.__init__(self, owner)
        self._html = HTML(owner=self)
        self._close = Close(owner=self)

    @property
    def tests(self):
        return self.owner.tests

    @property
    def close(self):
        return self._close

    @property
    def name(self):
        return "command"