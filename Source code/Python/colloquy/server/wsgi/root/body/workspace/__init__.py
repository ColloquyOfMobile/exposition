import traceback
from colloquy.base import Base
from pathlib import Path
import traceback
from utils import CustomDoc

class Workspace(Base):
    
    def __init__(self, owner):
        super().__init__(owner)
        self.opened = None
        self._hardware = self.owners[4].hardware
        self._exposition = self.colloquy.exposition

    def __call__(self):
        try:   
            html = self._call_unsafe()        
        except Exception as exception:
            html = self._call_if_error()
            
        return html

    @property
    def name(self):
        return "workspace"

    @property
    def workspace(self):
        return self

    @property
    def hardware(self):
        return self._hardware

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def tests(self):
        return self.colloquy.tests

    @property
    def exposition(self):
        return self._exposition
        

    def _call_unsafe(self):  
        doc, tag, text = CustomDoc().tagtext()
        with tag("div", style="display: flex; flex-direction: column;"):
            if self.opened is not None:
                doc.asis(self.opened())
                return doc.getvalue()
            
            doc.asis(self.tests.html())
            doc.asis(self.exposition.html())
            
        return doc.getvalue()
    
    def _call_if_error(self):
        doc, tag, text = CustomDoc().tagtext()  
        # .events.shutdown.set()
        with tag("body"):
            with tag("h1"):
                text(f"Error html for {self.name}!")
                                
            with tag("div", style="display: flex; flex-direction: column;"):
                style = "white-space: normal; overflow-wrap: break-word; word-break: break-word;"
                for line in traceback.format_exc().splitlines():
                    with tag("pre", style=style):
                        text(line)
        
        return doc.getvalue()