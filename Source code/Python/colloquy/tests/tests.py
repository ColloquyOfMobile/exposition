from server.html_element import HTMLElement
from .test1 import Test1
from .test2 import Test2



class Tests(HTMLElement):

    def __init__(self, owner):
        HTMLElement.__init__(self, owner)
        self._test1 = Test1(owner=self)
        self._test2 = Test2(owner=self)

    @property
    def colloquy(self):
        return self.owner

    def add_html(self):
        doc, tag, text = self.html_doc.tagtext()
        self._test1.add_html()
        self._test2.add_html()