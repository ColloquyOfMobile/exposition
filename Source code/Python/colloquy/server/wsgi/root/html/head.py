from utils import CustomDoc
from colloquy.wsgi.root.html_item import HtmlItem

class Head(HtmlItem):

    def __init__(self, owner):
        HtmlItem.__init__(self, owner)

    def __call__(self):
        self._doc = CustomDoc()
        doc, tag, text = self.doc.tagtext()
        with tag("head"):
            with tag("title"):
                text(f"Colloquy of Mobiles")
            doc.asis(
                '<meta name="viewport"'
                ' content="width=device-width,'
                " initial-scale=1,"
                ' interopened-widget=resizes-content" />'
            )
        # Insert HTML in parent doc only when it's sure that no error occured.
        self.parent.doc.asis(self.doc.getvalue())

    @property
    def name(self):
        return "head"