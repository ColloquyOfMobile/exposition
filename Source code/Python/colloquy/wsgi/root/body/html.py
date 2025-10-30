from colloquy.wsgi.root.html_item import HtmlItem
import traceback

class HTML(HtmlItem):
    
    # def __init__(self, owner):
        # HtmlItem.__init__(self, owner)
        
    def _call_unsafe(self,):         
        doc, tag, text = self.doc.tagtext()
        with tag("body", style="display: flex; flex-direction: column;"):
            with tag("h1", style="display: flex; flex: 1; justify-items: center;"):
                text(
                    f"Colloquy of Mobiles"
                    )                    
            if self.owner.opened:
                return self.owner.opened.html()
                
            self.owner.commands.html()
            self.owner.workspace.html()

    @property
    def name(self):
        return "HTML"