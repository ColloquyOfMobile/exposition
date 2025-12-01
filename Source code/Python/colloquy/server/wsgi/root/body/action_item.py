from utils import CustomDoc
import inspect
from pathlib import Path
from urllib.parse import unquote
import urllib.parse
from colloquy.wsgi.item import Item as _Item

class ActionItem(_Item):
    
    def __init__(self, owner):
        _Item.__init__(self, owner=owner)
        if self.parent is not None:
           self.parent.add(self)

    @property
    def request(self):
        action = self.post_data.get("action")
        if not action:
            return
        request = Path(action[0])
        request = request.relative_to(self.path)
        return request

    @property
    def path(self):
        return self.parent.path / self.name

    @property
    def parent(self):
        if self.owner.owner is not None:
            return self.owner.owner.action
            
    @property
    def value(self):
        return self.path.as_posix()
            
    @property
    def name(self):
        return self.owner.name 