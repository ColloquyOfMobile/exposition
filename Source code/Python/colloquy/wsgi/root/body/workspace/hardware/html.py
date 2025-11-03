from colloquy.wsgi.root.body.workspace.item import Item, HTML as _HTML
import traceback

class HTML(_HTML):
    
    def _call_body(self):
        
        self.owner.arduino.html()
        self.owner.neopixels.html()
        # self._test_neopixel_consumption.html()
        # self._test_neopixel_communication.html()
        # self._test_speaker.html()
        # self._test_photosensors.html()

    # @property
    # def doc(self):
        # return self.parent.doc