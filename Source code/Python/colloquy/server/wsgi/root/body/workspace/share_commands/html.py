from colloquy.wsgi.root.html_item import HtmlItem

class HTML(HtmlItem):
    
    # def __init__(self, owner):
        # HtmlItem.__init__(self, owner)
        
    def _call_unsafe(self,):    
        doc, tag, text = self.doc.tagtext()
        with tag("div", style="display: flex; "):
            self.owner.close.html(parent_doc=doc)     
            
    @property
    def name(self):
        return "html"