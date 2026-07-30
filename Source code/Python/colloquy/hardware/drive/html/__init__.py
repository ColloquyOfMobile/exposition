# from colloquy.wsgi.root.html_item import HtmlItem
import traceback
from pathlib import Path
from colloquy.base_html import BaseHTML

from .details import Details


class HTML(BaseHTML):
    def __init__(self, owner):
        super().__init__(owner=owner)
        self._details = Details(owner=self)
        self["details"] = self.details.handle_request

    @property
    def details(self):
        return self._details

    @property
    def name(self):
        return "html"

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def workspace(self):
        return self.colloquy.server.wsgi.root.body.workspace

    def open(self, request):
        if self.workspace.opened is not None:
            self.workspace.opened.close()
        self._is_open = True
        self.details.open(request=None)
        self.workspace.opened = self

    def close(self, request=None):
        self._is_open = False
        self.workspace.opened = None
        self.details.close()

    def _html_title(self):
        doc, tag, text = CustomDoc().tagtext()
        with tag(
            "div", style="margin-bottom: 0.5rem; display: flex; align-items: center;"
        ):
            with tag("div"):
                if self.is_details_open:
                    href = f"/{self.path.as_posix()}/close details"
                else:
                    href = f"/{self.path.as_posix()}/open details"
                with tag("a", href=href):
                    if self.is_details_open:
                        doc.asis(self._svg_down_arrow())
                    else:
                        doc.asis(self._svg_right_arrow())

            with tag("div", style="font-size: 1.2rem; margin-right: 1ch;"):
                with tag("strong"):
                    text(f"{self.owner.name} = {self.owner.value}")

            with tag("div"):
                if self.is_open:
                    href = f"/{self.path.as_posix()}/close"
                    label = "close"
                else:
                    href = f"/{self.path.as_posix()}/open"
                    label = "open"

                with tag("a", href=href):
                    text(f"{label}")

        return doc.getvalue()

    def _call_unsafe(self):
        doc, tag, text = CustomDoc().tagtext()
        doc.asis(self._html_title())
        doc.asis(self.details())

        return doc.getvalue()
