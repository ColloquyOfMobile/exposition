from utils import CustomDoc
from colloquy.wsgi.root.html_item import HtmlItem

class HTML(HtmlItem):

    def __call__(self):
        self._doc = CustomDoc()
        doc, tag, text = self.doc.tagtext()
        with tag("div", style="display: flex; "):
            self.owner.shutdown.html(parent_doc=doc)
            self.owner.restart.html(parent_doc=doc)     
        # Insert HTML in parent doc only when it's sure that no error occured. 
        self.parent.doc.asis(self.doc.getvalue())     
            
    @property
    def name(self):
        return "html"