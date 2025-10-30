from utils import CustomDoc
import inspect
from pathlib import Path
from urllib.parse import unquote
import urllib.parse
from colloquy.wsgi.root.body.action_item import ActionItem
from colloquy.wsgi.root.html_item import HtmlItem
from colloquy.wsgi.root.body.item import Item as _Item

class Item(_Item):    

    def __init__(self, owner):
        _Item.__init__(self, owner=owner)
        self._action = Action(owner=self)
        self._opened = None
        self._commands = None

    @property
    def workspace(self):
        return self.owner.workspace

    @property
    def commands(self):
        if self._commands is None:
            raise NotImplementedError(f"{self=}")
        return self._commands

    @property
    def hardware(self):
        return self.owner.hardware
        
    @property
    def is_opened(self):
        return self.owner.opened is self

    @property
    def opened(self):
        return self._opened

    @opened.setter
    def opened(self, value):
        # Value is None only in a Close(), this is to avoid recursion.
        if value is not None:
            if self._opened is not None:
                self._opened.close()
                
        self._opened = value
        
        
    def open(self, **kwargs):
        self.owner.opened = self

    def close(self, **kwargs):
        return self.commands.close()

class Action(ActionItem):

    def __call__(self):
        if not self.owner.is_opened:
            self.owner.open()
        if not self.request.parts:
            return
        key, *_ = self.request.parts
        if key not in self:
            raise NotImplementedError(f"{key=}, ({action})")
        action = self[key]
        action()

class HTML(HtmlItem):
    
    def _call_unsafe(self):
        doc, tag, text = self.doc.tagtext()
        if not self.owner.is_opened:
            self._call_if_is_not_opened()
            return
            
        if self.owner.opened:
            return self.owner.opened.html()

        with tag("div", style="display: flex; flex-direction: column;"):            
            with tag("h2", style="flex: 1;" ):
                text(self.owner.name)
            self.owner.commands.html()
        
        self._call_body()

    def _call_if_is_not_opened(self):
        doc, tag, text = self.doc.tagtext()
        with tag("form", method="post", style="display: flex; "):
            with tag("button", name="action", value=self.owner.action.value):
                text(self.owner.name)
    
    def _call_body(self):
        raise NotImplementedError(f"{self=}")
    
    @property
    def name(self):
        return "HTML"