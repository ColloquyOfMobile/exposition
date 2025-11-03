from pathlib import Path
from colloquy.wsgi.root.html_item import HtmlItem
from colloquy.wsgi.root.body.action_item import ActionItem
from colloquy.wsgi.root.body.workspace.item import Item, HTML as _HTML
from colloquy.wsgi.root.body.workspace.share_commands import Commands
from .test_neopixels import TestNeopixels
# from .test1 import Test1
# from .test2 import Test2
# from .test_speaker import TestSpeaker
# from .test_photosensors import TestPhotosensors



class Tests(Item):

    def __init__(self, owner):
        Item.__init__(self, owner=owner)
        self._opened = None
        self._html = HTML(owner=self)
        self._commands = Commands(owner=self)
        
        
        self._test_neopixels = TestNeopixels(owner=self)
        # self._test_speaker = TestSpeaker(owner=self)
        # self._test_photosensors = TestPhotosensors(owner=self)

    def __call__(self):
        if not self.is_opened:
            self.open()

    @property
    def opened(self):
        return self._opened

    @opened.setter
    def opened(self, value):
        # Value is None only in a Close(), this is to avoid recursion.
        if value is not None:
            if self._opened is not None:
                self._opened.close()
                
        self._opened = value

    @property
    def name(self):
        return "tests"

    @property
    def test_neopixels(self):
        return self._test_neopixels

    @property
    def tests(self):
        return self

class HTML(_HTML):
    
    def _call_body(self):
            
        self.owner.test_neopixels.html()
        # self._test_neopixel_consumption.html()
        # self._test_neopixel_communication.html()
        # self._test_speaker.html()
        # self._test_photosensors.html()
        