from server.html_element import HTMLElement
from .test1 import Test1
from .test2 import Test2
from .test_neopixel_consumption import TestNeopixelConsumption
from .test_speaker import TestSpeaker



class Tests(HTMLElement):

    def __init__(self, owner):
        HTMLElement.__init__(self, owner)
        # self._test1 = Test1(owner=self)
        # self._test2 = Test2(owner=self)
        self._test_neopixel_consumption = TestNeopixelConsumption(owner=self)
        self._test_speaker = TestSpeaker(owner=self)
        self._is_open = False
        self.opened = None
        self.name = "tests"

    @property
    def colloquy(self):
        return self.owner

    @property
    def is_open(self):
        return self._is_open

    def write_html(self):
        doc, tag, text = self.html_doc.tagtext()
        
        if not self.is_open:
            self._write_html_open()
            return
            
        if self.opened:
            self.opened.write_html()
            return
            
        with tag("h2"):
            text(self.name.title())
            
            
        self._write_html_action(value="colloquy/tests/close", label="close", func=self.close)
            
        self._test_neopixel_consumption.write_html()
        self._test_speaker.write_html()
    
    def _write_html_open(self):
        doc, tag, text = self.html_doc.tagtext()
        self._write_html_action(value="colloquy/tests/open", label=self.name, func=self.open)

    def open(self, **kwargs):
        if self._is_open:
            return
        self.owner.opened = self
        # self._actions = {}
        self._is_open = True

    def close(self, **kwargs):
        if not self._is_open:
            return
        self._is_open = False
        self.owner.opened = None