from colloquy.wsgi.root.body.item import Item
from .html import HTML
from .shutdown import Shutdown
from .restart import Restart

class Commands(Item):
    
    def __init__(self, owner):
        Item.__init__(self, owner)
        self._html = HTML(owner=self)
        self._shutdown = Shutdown(owner=self)
        self._restart = Restart(owner=self)

    @property
    def shutdown(self):
        return self._shutdown

    @property
    def restart(self):
        return self._restart

    @property
    def name(self):
        return "command"