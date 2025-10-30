from utils import CustomDoc
import inspect
from pathlib import Path
from urllib.parse import unquote
import urllib.parse
from colloquy.wsgi.item import Item as _Item

class Item(_Item):

    def __init__(self, owner):
        _Item.__init__(self, owner)
        self._html = None
        self._action = None


    @property
    def html(self):
        if self._html is None:
            raise NotImplementedError(f"Set manually 'return self.owner.html' for {self=}")
            # return self.owner.html
        return self._html


    @property
    def action(self):
        if self._action is None:
            return self.owner.action
        return self._action