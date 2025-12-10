from utils import CustomDoc
import inspect
from pathlib import Path
from urllib.parse import unquote
import urllib.parse
from colloquy.wsgi.root.body.action_item import ActionItem
from colloquy.wsgi.root.html_item import HtmlItem
from colloquy.hardware.item import Item as _Item

class Item(_Item):

    @property
    def female(self):
        return self.owner.female