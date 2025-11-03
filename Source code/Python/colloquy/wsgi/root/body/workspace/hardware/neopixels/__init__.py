from pathlib import Path
from colloquy.wsgi.root.html_item import HtmlItem
from colloquy.wsgi.root.body.action_item import ActionItem
from colloquy.wsgi.root.body.workspace.hardware.item_list import ItemList
from .commands import Commands



class Neopixels(ItemList):

    def __init__(self, owner):
        ItemList.__init__(self, owner=owner, name="neopixels")
        self._commands = Commands(owner=self)
    
    def __iter__(self):        
        neopixels = []
        for body in self.owner.bodies:
            neopixels.extend(body.neopixels)
        yield from neopixels