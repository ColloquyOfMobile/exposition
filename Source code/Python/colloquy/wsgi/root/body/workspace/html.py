from colloquy.wsgi.root.html_item import HtmlItem
import traceback

class HTML(HtmlItem):
    
    # def __init__(self, owner):
        # HtmlItem.__init__(self, owner)
        
    def _call_unsafe(self,):       
        doc, tag, text = self.doc.tagtext()
        with tag("div", style="display: flex; flex-direction: column;"):                        
            if self.owner.opened:
                return self.owner.opened.html()
                       
            self.owner.params.html()
            # self.owner.exposition.html()
            self.owner.tests.html()

    @property
    def name(self):
        return "HTML"