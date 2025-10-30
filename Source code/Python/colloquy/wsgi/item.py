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
    def start_response(self):
        return self.owner.start_response

    @property
    def wsgi(self):
        return self.owner.wsgi
    
    @property
    def request(self):
        return self.wsgi.request.relative_to(self.path)

    
    @property
    def post_data(self):
        return self.owner.post_data