from colloquy.wsgi.item import Item
from utils import CustomDoc
from .head import Head
import traceback

class HTML(Item):

    def __init__(self, owner):
        Item.__init__(self, owner)
        self._doc = None
        self._head = Head(owner=self)

    def __call__(self):
        self._doc = CustomDoc()
        try:
            self._call_unsafe()
        except Exception as exception:
            self.events.shutdown.set()
            doc, tag, text = self.doc.tagtext()
            doc.asis("<!DOCTYPE html>")
            with tag("div"):
                with tag("h1"):
                    text(f"Error html for {self.owner.name}!")

                with tag("h2"):
                    text(f"NOTE: Server was shutdown! Restart manually...)")

                with tag("div", style="display: flex; flex-direction: column;"):
                    style = "white-space: normal; overflow-wrap: break-word; word-break: break-word;"
                    for line in traceback.format_exc().splitlines():
                        with tag("pre", style=style):
                            text(line)
        return [self.doc.getvalue().encode()]

    def _call_unsafe(self,):
        doc, tag, text = CustomDoc().tagtext()
        doc.asis("<!DOCTYPE html>")
        with tag("html"):
            self.head()
            self.owner.body.html()
        # Insert HTML in parent doc only when it's sure that no error occured.
        self.doc.asis(doc.getvalue())


    @property
    def doc(self):
        return self._doc

    @property
    def head(self):
        return self._head

    @property
    def name(self):
        return "HTML"