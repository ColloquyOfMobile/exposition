import traceback
from colloquy.wsgi.root.item import Item
from colloquy.wsgi.root.html_item import HtmlItem



class ExceptionHandler(Item):
    
    def __init__(self, owner):
        Item.__init__(self, owner)
        self._value = None
        self._html = HTML(owner=self)


    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self.open()
        self._value = value

    @property
    def name(self):
        return "exception"
        
    def open(self):
        self.owner.opened = self
        

class HTML(HtmlItem):
        
    def __call__(self,):       
        doc, tag, text = self.doc.tagtext()
        with tag("div", style="display: flex; flex-direction: column;"):
            with tag("h2"):
                text(f"{repr(self.owner.value)}")
                
            with tag("div", style="display: flex; flex-direction: column;"):
                style = "white-space: normal; overflow-wrap: break-word; word-break: break-word;"
                for line in traceback.format_exception(self.owner.value):
                    with tag("pre", style=style):
                        text(line)
            
            # with tag("pre", ):
                # text(traceback.format_exception(self.owner.value))

    @property
    def name(self):
        return "HTML"