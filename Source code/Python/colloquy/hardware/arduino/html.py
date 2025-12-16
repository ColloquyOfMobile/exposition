# from colloquy.wsgi.root.html_item import HtmlItem
from pathlib import Path
from colloquy.base_html import BaseHTML
from utils import CustomDoc

class HTML(BaseHTML):

    def __init__(self, owner):
        super().__init__(owner=owner)

    @property
    def name(self):
        return "html"

    @property
    def tests(self):
        return self.colloquy.server.wsgi.root.body.workspace.tests

    def open(self, request):
        if self.tests.opened is not None:
            self.tests.opened.close()
        self._is_open = True
        self.tests.opened = self

    def close(self, request=None):
        self._is_open = False
        self.tests.opened = None

    def open_details(self, request):
        self._is_details_open = True

    def close_details(self, request=None):
        self._is_details_open = False

    def _call_unsafe(self):
        doc, tag, text = CustomDoc().tagtext()
        doc.asis(self._html_title())

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

    def _html_title(self):
        doc, tag, text = CustomDoc().tagtext()
        with tag("div", style="margin-bottom: 0.5rem; display: flex; align-items: center;"):
            with tag("div"):
                if self.is_details_open:
                    href=f"/{self.path.as_posix()}/close details"
                else:
                    href=f"/{self.path.as_posix()}/open details"
                with tag("a", href=href):
                    if self.is_details_open:
                        doc.asis(self._svg_down_arrow())
                    else:
                        doc.asis(self._svg_right_arrow())
                        
            with tag("div", style="font-size: 1.2rem; margin-right: 1ch;"):
                with tag("strong"):
                    if self.owner.is_open:
                        label = "open"
                    else:
                        label = "close"
                    text(f"{self.owner.name}, (Port is {label})")         
            
            with tag("div"):
                if self.is_open:
                    href=f"/{self.path.as_posix()}/close"
                    label = "close"
                else:
                    href=f"/{self.path.as_posix()}/open"
                    label = "open"
                    
                with tag("a", href=href):
                    text(f"{label}")
                    
                    
        return doc.getvalue()