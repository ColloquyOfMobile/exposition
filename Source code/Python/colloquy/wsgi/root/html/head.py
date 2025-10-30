from colloquy.wsgi.root.html_item import HtmlItem

class Head(HtmlItem):
    
    def __init__(self, owner):
        HtmlItem.__init__(self, owner)

    def __call__(self):
        doc, tag, text = self.doc.tagtext()
        with tag("head"):
            with tag("title"):
                text(f"Hardware of Mobiles")
            doc.asis(
                '<meta name="viewport"'
                ' content="width=device-width,'
                " initial-scale=1,"
                ' interopened-widget=resizes-content" />'
            )

    @property
    def name(self):
        return "head"