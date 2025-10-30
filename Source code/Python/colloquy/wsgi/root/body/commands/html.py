from colloquy.wsgi.root.html_item import HtmlItem

class HTML(HtmlItem):

    def __call__(self):
        doc, tag, text = self.doc.tagtext()
        with tag("div", style="display: flex; "):
            self.owner.shutdown.html()
            self.owner.restart.html()          
            
    @property
    def name(self):
        return "html"