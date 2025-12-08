# from colloquy.wsgi.root.html_item import HtmlItem
from pathlib import Path
from colloquy.base import Base
from utils import CustomDoc

class HTML(Base):

    def __init__(self, owner):
        super().__init__(owner=owner)

    def __call__(self, request=None):
        self._request = request
        try:   
            html = self._call_unsafe()        
        except Exception as exception:
            html = self._call_if_error()
            
        return html

    def _call_unsafe(self, request=None):
        # self._handle_request()
        doc, tag, text = CustomDoc().tagtext()
        with tag("div", style="font-size: 1.2rem; margin-bottom: 0.5rem;"):
            if self.owner.is_open:
                href=f"/{self.owner.path.as_posix()}/close"
            else:
                href=f"/{self.owner.path.as_posix()}/open"
            with tag("a", href=href):
                if self.owner.is_open:
                    doc.asis(self._svg_down_arrow())
                else:
                    doc.asis(self._svg_right_arrow())
                    
                with tag("strong"):
                    text(f"{self.owner.body.name}/{self.owner.name}")
                    
        if self.owner.is_open:
            with tag("div"):
                doc.asis(self.owner.toggle_on_off.html())
                doc.asis(self.owner.brightness.html())
                doc.asis(self.owner.white.html())
                doc.asis(self.owner.red.html())
                doc.asis(self.owner.green.html())
                doc.asis(self.owner.blue.html())
        
        return doc.getvalue()      
        
    @property
    def name(self):
        return "html" 
    

    def handle_request(self):
        request = self._request
        if request is None:
            return
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