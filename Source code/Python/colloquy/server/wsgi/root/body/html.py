from colloquy.wsgi.root.html_item import HtmlItem
from utils import CustomDoc
import traceback

class HTML(HtmlItem):

    # def __init__(self, owner):
        # HtmlItem.__init__(self, owner)

    def __call__(self):
        self._doc = CustomDoc()
        doc, tag, text = self.doc.tagtext()
        with tag("body", style="display: flex; flex-direction: column;"):
            with tag("h1", style="display: flex; flex: 1; justify-items: center;"):
                text(
                    f"Colloquy of Mobiles"
                    )

            if self.owner.opened:
                self.owner.opened.html(parent_doc=doc)
            else:
                self.owner.commands.html()
                self.owner.workspace.html()

        if self.owner.opened:
            print(f"{self.doc.getvalue()=}")
        self.parent.doc.asis(self.doc.getvalue())


    # def _call_unsafe(self,):
        # doc, tag, text = self.doc.tagtext()
        # self.owner.workspace.html()

    @property
    def name(self):
        return "HTML"