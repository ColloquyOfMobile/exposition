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
        # self._opened = None
        # self._html = HTML(owner=self)
        # self._action = Action(owner=self)
        
        # self._params = Parameters(owner=self)
        self._hardware = self.owners[4].hardware
        # self._exception = ExceptionHandler(owner=self) 
        # self._tests = Tests(owner=self)

    def __call__(self):
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

    # @property
    # def workspace(self):
        # return self

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
        

    def _call_unsafe(self):   
        doc, tag, text = CustomDoc().tagtext()
        with tag("div", style="display: flex; flex-direction: column;"):
            for neopixel in self.hardware.neopixels:
                with tag("div", id=neopixel.path.as_posix(), style="font-size: 1.2rem; margin-bottom: 0.5rem;"):
                    with tag("strong"):
                        text(f"{neopixel.body.name}/{neopixel.name}")
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