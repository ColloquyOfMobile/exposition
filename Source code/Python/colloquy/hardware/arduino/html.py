# from colloquy.wsgi.root.html_item import HtmlItem
from pathlib import Path
from colloquy.base import Base
from utils import CustomDoc

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

    def _call_unsafe(self):
        # self._handle_request()
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
                    if self.owner.is_open:
                        label = "open"
                    else:                    
                        label = "close" 
                    text(f"{self.owner.name}, (Port is {label})")
                    
        if self.is_open:
            with tag("div"):
                if self.owner.is_open:
                    label = "close"
                else:                    
                    label = "open"
                
                href=f"/{self.owner.path.as_posix()}/{label}"
                with tag("a", href=href):
                    text(f"{label} port")
        
        return doc.getvalue()    
        
    @property
    def is_open(self):
        return self._is_open     
        
    @property
    def name(self):
        return "html" 

    @property
    def colloquy(self):
        return self.owner.colloquy
        
    @property
    def workspace(self):
        return self.colloquy.server.wsgi.root.body.workspace

    def open(self, request=None):
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

    def _svg_down_arrow(self):
        doc, tag, text = CustomDoc().tagtext()
        with tag('svg', width='16', height='16', viewBox='0 0 24 24', fill='none',
             stroke='currentColor', **{'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round'}):
            doc.stag('polyline', points='6 9 12 15 18 9')
        
        return doc.getvalue()


    def _svg_right_arrow(self):
        doc, tag, text = CustomDoc().tagtext()
        with tag('svg', width='16', height='16', viewBox='0 0 24 24', fill='none',
             stroke='currentColor', **{'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round'}):
            doc.stag('polyline', points='9 6 15 12 9 18')
        
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