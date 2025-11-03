from pathlib import Path
from colloquy.wsgi.root.html_item import HtmlItem
from colloquy.wsgi.root.body.action_item import ActionItem
from colloquy.wsgi.root.body.workspace.item_list import ItemList
from colloquy.wsgi.root.body.workspace.share_commands import Commands



class Neopixels(ItemList):

    def __init__(self, owner):
        ItemList.__init__(self, owner=owner, name="neopixels")
    
    def __iter__(self):        
        neopixels = []
        for body in self.owner.bodies:
            neopixels.extend(body.neopixels)
        yield from neopixels


        