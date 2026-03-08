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
    def light_sensor(self):
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

    @property
    def arduino(self):
        return self.owner.arduino

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
        try:
            doc.asis(self._html_title_unsafe())
        except Exception as exception:
            doc.asis(self._html_title_if_error())

        return doc.getvalue()
    
    def _html_title_unsafe(self):
        doc, tag, text = CustomDoc().tagtext()
        
        style="margin-bottom: 0.5rem; display: flex; align-items: center;"
        if self.is_open:
            style += " justify-content: center;"

        with tag("div",style=style):
            if self.arduino.port_name is None:
                with tag("div", style="font-size: 1.2rem; margin-right: 1ch;"):
                    with tag("strong"):
                        text(f"{self.owner.name}=Set the arduino ")
                        with tag("a", href="hardware/arduino/html/open"):
                            text("com port ")
                        text("to read the value!")
                            
            else:
                if not self.is_open:
                    doc.asis(self.details.arrow)
                value = self.owner.read()
                with tag("div", style="font-size: 1.2rem; margin-right: 1ch;"):
                    with tag("strong"):
                        text(f"{self.owner.name}={value}")

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

    def _html_title_if_error(self):
        doc, tag, text = CustomDoc().tagtext()
        with tag("div"):
            with tag("h2"):
                text(f"Error in {self}'s title!")

            with tag("div", style="display: flex; flex-direction: column;"):
                style = "white-space: normal; overflow-wrap: break-word; word-break: break-word;"
                for line in traceback.format_exc().splitlines():
                    with tag("pre", style=style):
                        text(line)

        return doc.getvalue()


    def _call_unsafe(self):
        doc, tag, text = CustomDoc().tagtext()

        doc.asis(self._html_title())
        doc.asis(self.details())

        return doc.getvalue()