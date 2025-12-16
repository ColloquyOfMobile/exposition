# from colloquy.wsgi.root.html_item import HtmlItem
from pathlib import Path
from colloquy.base_html import BaseHTML
from utils import CustomDoc
import traceback

class HTML(BaseHTML):

    def __init__(self, owner):
        super().__init__(owner=owner)

    @property
    def is_open(self):
        return self._is_open

    @property
    def name(self):
        return "html"

    @property
    def tests(self):
        return self.colloquy.tests

    def open(self, request):
        if self.tests.opened is not None:
            self.tests.opened.close()
        self._is_open = True
        self.tests.opened = self

    def close(self, request=None):
        assert not self.owner.is_started
        self._is_open = False
        self.tests.opened = None

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
                    text(f"{self.owner.name}")

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

    def _call_unsafe(self):
        doc, tag, text = CustomDoc().tagtext()
        doc.asis(self._html_title())

        if not self.is_open:
            return doc.getvalue()

        # with tag("div", style="font-size: 1.2rem; margin-bottom: 0.5rem;"):
            # if self.is_open:
                # href=f"/{self.path.as_posix()}/close"
            # else:
                # href=f"/{self.path.as_posix()}/open"
            # with tag("a", href=href):
                # if self.is_open:
                    # doc.asis(self._svg_down_arrow())
                # else:
                    # doc.asis(self._svg_right_arrow())

                # with tag("strong"):
                    # text(f"{self.owner.name}")

        with tag("div"):
            if self.owner.is_started:
                label = "stop"
            else:
                label = "start"

            href=f"/{self.owner.path.as_posix()}/{label}"

            with tag("a", href=href):
                text(f"{label}")

        return doc.getvalue()