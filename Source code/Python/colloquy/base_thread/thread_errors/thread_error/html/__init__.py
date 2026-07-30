# from colloquy.wsgi.root.html_item import HtmlItem
from pathlib import Path
from colloquy.base_html import BaseHTML

import traceback
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
    def hardware(self):
        return self.owner.hardware

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

        style = "margin-bottom: 0.5rem; display: flex; align-items: center;"
        if self.is_open:
            style += " justify-content: center;"

        with tag("div", style=style):
            if not self.is_open:
                # with tag("div"):
                doc.asis(self.details.arrow)

            with tag(
                "div",
                style="font-size: 1.2rem; margin-right: 1ch; overflow:auto; text-wrap: nowrap;",
            ):
                with tag("strong"):
                    text(f"{self.owner.name}")

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
