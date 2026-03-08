# from colloquy.wsgi.root.html_item import HtmlItem
from pathlib import Path
from colloquy.base_html import BaseHTML
from utils import CustomDoc
import traceback

class Details(BaseHTML):

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._opened = None
    
    @property
    def opened(self):
        return self._opened
    
    @opened.setter
    def opened(self, value):
        self._opened = value
    
    @property
    def light_sensor(self):
        return self.owner.light_sensor
    
    @property
    def dxl(self):
        return self.owner.dxl
    
    @property
    def hardware(self):
        return self.owner.hardware

    @property
    def name(self):
        return "details"

    @property
    def workspace(self):
        return self.owner.workspace
    
    @property
    def arrow(self):
        doc, tag, text = CustomDoc().tagtext()
        if self.is_open:
            href=f"/{self.path.as_posix()}/close"
            svg = self._svg_down_arrow()
        else:
            href=f"/{self.path.as_posix()}/open"
            svg = self._svg_right_arrow()
        with tag("div", name=self.name):
            with tag("a", href=href):
                doc.asis(svg)
        return doc.getvalue()

    def open(self, request):
        self._is_open = True

    def close(self, request=None):
        self._is_open = False

    def _call_unsafe(self):
        if not self.is_open:
            return ""        
        
        doc, tag, text = CustomDoc().tagtext()
            
        with tag("div",  name=self.name, style="display: flex; flex:1; flex-direction: column;"):
            
            doc.asis(self.light_sensor.read_pattern.html())
            # raise NotImplementedError(self)

        return doc.getvalue()

    def _html_thread_error(self, error):
        doc, tag, text = CustomDoc().tagtext()
        origin = error.origin
        error = error.error
        with tag("div"):
            with tag("div"):
                with tag("strong"):
                    text(f"Error in thread {origin}!")

            with tag("div", style="display: flex; flex-direction: column;"):
                style = "white-space: normal; overflow-wrap: break-word; word-break: break-word;"
                for line in traceback.format_exception(error):
                    with tag("pre", style=style):
                        text(line)

        return doc.getvalue()