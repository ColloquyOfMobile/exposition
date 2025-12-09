# from colloquy.wsgi.root.html_item import HtmlItem
from pathlib import Path
from colloquy.base import Base
from utils import CustomDoc
import traceback

class HTML(Base):

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._is_open = False
        
        self["open"] = self.open
        self["close"] = self.close

    def __call__(self, request=None):
        self._request = request
        try:   
            html = self._call_unsafe()        
        except Exception as exception:
            html = self._call_if_error()
            
        return html
    
    def _html_title(self):
        doc, tag, text = CustomDoc().tagtext()
        with tag("div", style="font-size: 1.2rem; margin-bottom: 0.5rem;"):
            if self.is_open:
                href=f"/{self.path.as_posix()}/close"
            else:
                href=f"/{self.path.as_posix()}/open"
            with tag("a", href=href):
                if self.is_open:
                    doc.asis(self._svg_down_arrow())
                else:
                    doc.asis(self._svg_right_arrow())
                    
                with tag("strong"):          
                    text(f"{self.owner.name}")
        return doc.getvalue()
        

    def _call_unsafe(self):  
        doc, tag, text = CustomDoc().tagtext()
        doc.asis(self._html_title())
        
        if not self.is_open:
            return doc.getvalue()
            
        with tag("div", style="display: flex; flex-direction: column;"):
            if self.owner.opened is not None:
                doc.asis(self.owner.opened())
                
            if self.hardware.arduino.html is not self.owner.opened:
                doc.asis(self.hardware.arduino.html())
                
            if self.owner.test1.html is not self.owner.opened:
                doc.asis(self.owner.test1.html())
                
                
                
            for neopixel in self.hardware.neopixels:   
                if neopixel.html is self.owner.opened:
                    continue
                doc.asis(neopixel.html())
            
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
        
    @property
    def is_open(self):
        return self._is_open     
        
    @property
    def name(self):
        return "html" 

    @property
    def hardware(self):
        return self.owner.hardware

    @property
    def colloquy(self):
        return self.owner.colloquy
        
    @property
    def workspace(self):
        return self.colloquy.server.wsgi.root.body.workspace

    def open(self, request):
        if self.workspace.opened is not None:
            self.workspace.opened.close()
        self._is_open = True
        self.workspace.opened = self

    def close(self, request=None):
        self._is_open = False
        self.workspace.opened = None    

    def handle_request(self, request):
        request = Path(request)
        if not request.parts:
            raise NotImplementedError
            
        key, *leftover = request.parts
        
        if key in self:
            self[key](request="/".join(leftover))
            return
            
        raise NotImplementedError(f"{key=}, {leftover=}, in {self=}")   