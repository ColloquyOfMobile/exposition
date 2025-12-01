from pathlib import Path
import traceback
import socket
from threading import Thread, Event, Lock
from utils import CustomDoc
from colloquy.base import Base

# from .html import HTML
from .body import Body

class Root(Base):
    def __init__(self, owner):
        super().__init__(owner)
        self._server = owner.server
        self._body = Body(owner=self)
        self._head = owner.head
        # self._html = HTML(owner=self)

    def __call__(self):
        self.owner.start_response('200 OK', [('Content-Type', 'text/html')])
        try:   
            html = self._call_unsafe()        
        except Exception as exception:
            html = self._call_if_error()
            
        return [html.encode()]

    @property
    def server(self):
        return self._server

    @property
    def head(self):
        return self._head

    @property
    def body(self):
        return self._body

    @property
    def name(self):
        return "root"
        
    @property
    def opened(self):
        raise NotImplementedError
        
    
    def _call_unsafe(self):
        doc, tag, text = CustomDoc().tagtext()
        doc.asis("<!DOCTYPE html>")
        with tag("html"):
            doc.asis(self.head())
            doc.asis(self.body())
        
        return doc.getvalue()
        
    
    def _call_if_error(self):
        self.events.shutdown.set()
        doc, tag, text = CustomDoc().tagtext()  
        doc.asis("<!DOCTYPE html>")
        with tag("body"):
            with tag("h1"):
                text(f"Error html for {self.name}!")
                
            with tag("h2"):
                text(f"NOTE: Server was shutdown! Restart manually...)")
                                
            with tag("div", style="display: flex; flex-direction: column;"):
                style = "white-space: normal; overflow-wrap: break-word; word-break: break-word;"
                for line in traceback.format_exc().splitlines():
                    with tag("pre", style=style):
                        text(line)
        
        return doc.getvalue()

    