from colloquy.base import Base
import traceback
from utils import CustomDoc
# from .html import HTML
from .shutdown import Shutdown
from .restart import Restart

class Commands(Base):
    
    def __init__(self, owner):
        super().__init__(owner)
        self._server = owner.server
        # self._html = HTML(owner=self)
        self._shutdown = Shutdown(owner=self)
        self._restart = Restart(owner=self)

    def __call__(self):
        try:   
            html = self._call_unsafe()  
        except Exception as exception:
            html = self._call_if_error()
            
        return html

    @property
    def server(self):
        return self._server

    @property
    def shutdown(self):
        return self._shutdown

    @property
    def restart(self):
        return self._restart

    @property
    def name(self):
        return "command"
        

    def _call_unsafe(self):   
        doc, tag, text = CustomDoc().tagtext()
        with tag("div", style="display: flex; margin-bottom: 1rem;"):  
                doc.asis(self.shutdown.html())
                with tag("div", style="width: 1ch;"):
                    pass
                doc.asis(self.restart.html())
        return doc.getvalue()
    
    def _call_if_error(self):
        doc, tag, text = CustomDoc().tagtext()  
        with tag("div"):
            with tag("div"):
                with tag("strong"):
                    text(f"Error html for {self.name}!")
                                
            with tag("div", style="display: flex; flex-direction: column;"):
                style = "white-space: normal; overflow-wrap: break-word; word-break: break-word;"
                for line in traceback.format_exc().splitlines():
                    with tag("pre", style=style):
                        text(line)
        
        return doc.getvalue()