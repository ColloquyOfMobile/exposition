# from colloquy.wsgi.root.html_item import HtmlItem
import traceback
from pathlib import Path
from colloquy.base_html import BaseHTML
from utils import CustomDoc

class HTML(BaseHTML):

    def __init__(self, owner):
        super().__init__(owner=owner)

    def _call_unsafe(self):
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
                    text(f"{self.owner.owner.name}/{self.owner.name}")

        if self.is_open:
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

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def tests(self):
        return self.colloquy.tests

    def open(self, request):
        if self.tests.opened is not None:
            self.tests.opened.close()
        self._is_open = True
        self.tests.opened = self

    def close(self, request=None):
        self._is_open = False
        self.tests.opened = None