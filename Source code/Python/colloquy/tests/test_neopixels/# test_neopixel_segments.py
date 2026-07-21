from colloquy.base import Base
#from colloquy.wsgi.root.html_item import HtmlItem

class TestNeopixelSegments(Base):

    def __init__(self, owner):
        super().__init__(owner=owner)
        # self._html = HTML(owner=self)

    @property
    def name(self):
        return "test Neopixel segments"