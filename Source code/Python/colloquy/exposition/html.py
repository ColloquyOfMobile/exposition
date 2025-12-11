# from colloquy.wsgi.root.html_item import HtmlItem
from pathlib import Path
from colloquy.base_html import BaseHTML
from utils import CustomDoc
import traceback

class HTML(BaseHTML):

    def __init__(self, owner):
        super().__init__(owner=owner)

    @property
    def name(self):
        return "html"

    @property
    def workspace(self):
        return self.owner.workspace

    def open(self, request):
        if self.workspace.opened is not None:
            self.workspace.opened.close()
        self._is_open = True
        self.workspace.opened = self

    def close(self, request=None):
        self._is_open = False
        self.workspace.opened = None

    def _html_title(self):
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
                    text(f"{self.owner.name}")
        return doc.getvalue()

    def _call_unsafe(self):
        doc, tag, text = CustomDoc().tagtext()
        doc.asis(self._html_title())
        if self.is_open:
            with tag("div"):
                if self.owner.is_started:
                    label = "stop"
                else:
                    label = "start"

            href=f"/{self.owner.path.as_posix()}/{label}"

            with tag("a", href=href):
                text(f"{label}")
            
            for (origin, error) in self.owner.child_errors:
                doc.asis(self._html_thread_error(origin=origin, error=error))


        return doc.getvalue()
    
    def _html_thread_error(self, origin, error):
        doc, tag, text = CustomDoc().tagtext()
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