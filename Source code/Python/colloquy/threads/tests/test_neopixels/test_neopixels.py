from colloquy.thread_element import ThreadElement
from .test_neopixel_consumption import TestNeopixelConsumption
from .test_neopixel_communication import TestNeopixelCommunication
from .test_neopixel_segments import TestNeopixelSegments

class TestNeopixels(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name="test Neopixels")
        self._test_neopixel_consumption = TestNeopixelConsumption(owner=self)
        self._test_neopixel_communication = TestNeopixelCommunication(owner=self)
        self._test_neopixel_segments = TestNeopixelSegments(owner=self)
        self._is_open = False
        self.opened = None

    # @property
    # def hardware(self):
        # return self.owner.hardware

    @property
    def is_open(self):
        return self._is_open

    @property
    def path(self):
        return self._path

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
            
            
        self._write_html_action(value="tests/test Neopixels/close", label="close", func=self.close)
        
        self._test_neopixel_consumption.write_html()
        self._test_neopixel_communication.write_html()
        self._test_neopixel_segments.write_html()
    
    def _write_html_open(self):
        doc, tag, text = self.html_doc.tagtext()
        self._write_html_action(value="tests/test Neopixels/open", label=self.name, func=self.open)

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