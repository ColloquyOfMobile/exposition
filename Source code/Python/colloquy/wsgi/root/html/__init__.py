from colloquy.wsgi.item import Item
from utils import CustomDoc
from .head import Head

class HTML(Item):
    
    def __init__(self, owner):
        Item.__init__(self, owner)
        self._doc = None
        self._head = Head(owner=self)
        
    def __call__(self,):       
        self._doc = CustomDoc()
        doc, tag, text = self._doc.tagtext()
        doc.asis("<!DOCTYPE html>")
        with tag("html"):
            self.head()
            self.owner.body.html()
        return [self.doc.getvalue().encode()]
            
    @property
    def doc(self):
        return self._doc

    @property
    def head(self):
        return self._head

    @property
    def name(self):
        return "HTML"