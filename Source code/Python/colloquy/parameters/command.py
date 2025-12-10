from utils import CustomDoc
import inspect
from pathlib import Path
from urllib.parse import unquote
import urllib.parse
from colloquy.wsgi.root.html_item import HtmlItem
from colloquy.wsgi.root.body.item import Item

class Command(Item):

    def __init__(self, owner):
        Item.__init__(self, owner)
        self._html = None
        self._action = None

    @property
    def is_opened(self):
        return self.owner.opened is self

    # def open(self):
        # self.owner.opened = self

class HTML(HtmlItem):

    # def __init__(self, owner):
        # HtmlItem.__init__(self, owner)

    def __call__(self):
        doc, tag, text = self.doc.tagtext()
        if self.owner.is_opened:
            return self._call_is_opened()
        with tag("form", method="post", style="display: flex; "):
            with tag("button", name="action", value=self.owner.action.value):
                text(self.owner.name)

    @property
    def name(self):
        return "html"

    def _call_is_opened(self):
        raise NotImplementedError(f"{self}")