from utils import CustomDoc
import inspect
from pathlib import Path
from urllib.parse import unquote
import urllib.parse
from colloquy.wsgi.root.item import Item as _Item

class Item(_Item):    
    
    @property
    def opened(self):
        return self.owner.opened
    
    
    @opened.setter
    def opened(self, value):
        self.owner.opened = value