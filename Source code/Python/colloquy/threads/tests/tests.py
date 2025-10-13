from pathlib import Path
from server.html_element import HTMLElement
from colloquy.thread_element import ThreadElement
from .test_neopixels import TestNeopixels
from .test1 import Test1
from .test2 import Test2
from .test_speaker import TestSpeaker
from .test_photosensors import TestPhotosensors



class Tests(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name="tests")
        self._is_open = False
        self.opened = None
        
        self._test_neopixels = TestNeopixels(owner=self)
        self._test_speaker = TestSpeaker(owner=self)
        self._test_photosensors = TestPhotosensors(owner=self)

    @property
    def hardware(self):
        return self.owner.hardware

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
            
            
        self._write_html_action(value="hardware/tests/close", label="close", func=self.close)
        
        self._test_neopixels.write_html()
        # self._test_neopixel_consumption.write_html()
        # self._test_neopixel_communication.write_html()
        self._test_speaker.write_html()
        self._test_photosensors.write_html()
    
    def _write_html_open(self):
        doc, tag, text = self.html_doc.tagtext()
        self._write_html_action(value="hardware/tests/open", label=self.name, func=self.open)

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