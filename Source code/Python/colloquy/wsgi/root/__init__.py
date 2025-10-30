from pathlib import Path
import traceback
import socket
from threading import Thread, Event, Lock
from colloquy.wsgi.item import Item

from .html import HTML
from .body import Body

class Root(Item):
    def __init__(self, owner):
        Item.__init__(self, owner)
        self._body = Body(owner=self)
        self._html = HTML(owner=self)

    def __call__(self):
        self.start_response('200 OK', [('Content-Type', 'text/html')])
               
        self.body()
            
        return self.html()


    @property
    def html(self):
        return self._html

    @property
    def body(self):
        return self._body

    @property
    def name(self):
        return "root"
        
    @property
    def action(self):
        return self._action
        
    @property
    def opened(self):
        raise NotImplementedError

    