# from colloquy.wsgi.root.html_item import HtmlItem
from pathlib import Path
from colloquy.base_html import BaseHTML
from utils import CustomDoc
import traceback
from .details import Details

class HTML(BaseHTML):

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._details = Details(owner=self)
        self["details"] = self.details.handle_request
    
    @property
    def dxl_origin(self):
        return self.owner
    
    @property
    def female(self):
        return self.owner.female

    @property
    def details(self):
        return self._details

    @property
    def name(self):
        return "html"

    @property
    def hardware(self):
        return self.owner.hardware

    @property
    def u2d2(self):
        return self.owner.u2d2

    @property
    def open_in(self):
        return self.female.html.details

    def open(self, request):
        if self.open_in.opened is not None:
            self.open_in.opened.close()
        self._is_open = True
        self.details.open(request=None)
        self.open_in.opened = self

    def close(self, request=None):
        self._is_open = False
        self.open_in.opened = None
        self.details.close()

    def _html_title(self):
        doc, tag, text = CustomDoc().tagtext()
        value = self.owner.get()

        style="margin-bottom: 0.5rem; display: flex; align-items: center;"
        # if self.is_open:
            # style += " justify-content: center;"

        with tag("div",style=style):
            # if not self.is_open:
                # doc.asis(self.details.arrow)

            with tag("div", style="font-size: 1.2rem; margin-right: 1ch;"):
                with tag("strong"):
                    text(f"{self.owner.name}={value}")

            with tag("div", style="margin-right: 1ch;"):
                href=f"/{self.female.path.as_posix()}/set current position as dxl origin"

                with tag("a", href=href):
                    text(f"set current position as dxl origin")

        return doc.getvalue()


    def _call_unsafe(self):
        doc, tag, text = CustomDoc().tagtext()

        doc.asis(self._html_title())
        doc.asis(self.details())

        return doc.getvalue()