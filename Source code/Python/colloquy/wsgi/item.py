from utils import CustomDoc
import inspect
from pathlib import Path
from urllib.parse import unquote
import urllib.parse
from colloquy.colloquy_item import ColloquyItem as _Item

class Item(_Item):

    def __init__(self, owner):
        _Item.__init__(self, owner)
        self.owner.add(self)

    @property
    def owner(self):
        return self._owner

    @property
    def path(self):
        return self.owner.path / self.name
    
    @property
    def events(self):
        return self.owner.events