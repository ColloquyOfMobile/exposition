# from colloquy.wsgi.root.body.action_item import ActionItem
import traceback
from colloquy.base import Base
from pathlib import Path
import traceback
from utils import CustomDoc
# from .html import HTML
# from .parameters import Parameters
# from .hardware import Hardware
from .exception_handler import ExceptionHandler
from .tests import Tests

class Workspace(Base):
    
    def __init__(self, owner):
        super().__init__(owner)
        self.opened = None
        self._request = None
        self._hardware = self.owners[4].hardware
                
        for neopixel in self.hardware.neopixels:        
            self[neopixel.name] = neopixel.html.handle_request

    def __call__(self, request=None):
        self._request = request
        try:   
            html = self._call_unsafe()        
        except Exception as exception:
            html = self._call_if_error()
            
        return html

    # @property
    # def opened(self):
        # return self._opened

    # @opened.setter
    # def opened(self, value):
        # # Value is None only in a Close(), this is to avoid recursion.
        # if value is not None:
            # if self._opened is not None:
                # self._opened.close()
                
        # self._opened = value

    @property
    def name(self):
        return "workspace"

    @property
    def workspace(self):
        return self

    # @property
    # def params(self):
        # return self._params

    # @property
    # def exception(self):
        # return self._exception
        
        
########################################################################################
    # @property
    # def near_origin_threashold(self):
        # return self._params["near_origin_threashold"]

    # @near_origin_threashold.setter
    # def near_origin_threashold(self, value):
        # self._params["near_origin_threashold"] = value 

    @property
    def hardware(self):
        return self._hardware

    # @property
    # def exposition(self):
        # return self._exposition

    # @property
    # def tests(self):
        # return self._tests

    # @property
    # def agenda(self):
        # return self._agenda   

    # @property
    # def log(self):
        # return self._log
    
    

    def handle_request(self, request):        
        request = Path(request)
        if not request.parts:
            raise NotImplementedError
            
        key, *leftover = request.parts
        
        if key in self:
            self[key](request="/".join(leftover))
            return
            
        raise NotImplementedError(f"{key=}, {leftover=}, in {self=}")   
        

    def _call_unsafe(self):  
        doc, tag, text = CustomDoc().tagtext()
        with tag("div", style="display: flex; flex-direction: column;"):
            if self.opened is not None:
                doc.asis(self.opened.html())
                
            for neopixel in self.hardware.neopixels:   
                if neopixel is self.opened:
                    continue
                doc.asis(neopixel.html())
            
        return doc.getvalue()
    
    def _call_if_error(self):
        doc, tag, text = CustomDoc().tagtext()  
        self.events.shutdown.set()
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