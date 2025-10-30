from pathlib import Path
import traceback
import socket
from threading import Thread, Event, Lock
from colloquy.wsgi.root.item import Item
# from colloquy.wsgi.root.html_item import HtmlItem
# from server.html_element import HTMLElement
from .html import HTML
from .commands import Commands
from .action import Action
from .workspace import Workspace

class Body(Item):
    def __init__(self, owner):
        Item.__init__(self, owner)
        self._opened = None
        self._action = Action(owner=self)
        self._html = HTML(owner=self)
        self._commands= Commands(owner=self)        
        self._workspace = Workspace(owner=self)
        # self.init()

    def __call__(self):       
        self.action()

    @property
    def body(self):
        return self

    @property
    def commands(self):
        return self._commands

    @property
    def workspace(self):
        return self._workspace

    @property
    def name(self):
        return "body"

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