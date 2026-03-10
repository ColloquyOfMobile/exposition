from colloquy.base import Base
import traceback
from utils import CustomDoc
# from colloquy.wsgi.root.body.command import Command, HTML as _HTML

class Shutdown(Base):

    def __init__(self, owner):
        super().__init__(owner)

    def __call__(self, request):
        for thread in self.all_threads:
            thread.shutdown()
        for thread in self.all_threads:
            thread.join()
        self.owner.server.events.shutdown.set()
        # self.colloquy.hardware.shutdown()

    @property
    def name(self):
        return "shutdown"

    @property
    def href(self):
        return f"/{self.name}"

    def html(self):
        try:
            html = self._html_unsafe()
        except Exception as exception:
            html = self._html_if_error()

        return html

    def _html_unsafe(self):
        doc, tag, text = CustomDoc().tagtext()
        with tag("div"):
            with tag("a", href=self.href):
                text(self.name)
        return doc.getvalue()

    def _html_if_error(self):
        doc, tag, text = CustomDoc().tagtext()
        with tag("div"):
            with tag("div"):
                with tag("strong"):
                    text(f"Error html for {self.name}!")

            with tag("div", style="display: flex; flex-direction: column;"):
                style = "white-space: normal; overflow-wrap: break-word; word-break: break-word;"
                for line in traceback.format_exc().splitlines():
                    with tag("pre", style=style):
                        text(line)

        return doc.getvalue()