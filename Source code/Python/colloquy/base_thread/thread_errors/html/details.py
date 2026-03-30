# from colloquy.wsgi.root.html_item import HtmlItem
from pathlib import Path
from colloquy.base_html import BaseHTML

import traceback

class Details(BaseHTML):

    def __init__(self, owner):
        super().__init__(owner=owner)
    
    @property
    def drives(self):
        return self.owner.owner
    
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
        
        thread_errors = self.owner.owner
        
        
        doc, tag, text = CustomDoc().tagtext()
        with tag("div"):
            with tag("div"):
                for error in thread_errors.errors:
                    doc.asis(error.html())
                    
            with tag("div"):
                for child in thread_errors.owner.children:
                    doc.asis(child.thread_errors.html())

        return doc.getvalue()