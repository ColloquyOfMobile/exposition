from colloquy.wsgi.root.body import Item
from colloquy.wsgi.root.html_item import HtmlItem

class TestNeopixelSegments(Item):

    def __init__(self, owner):
        Item.__init__(self, owner=owner)
        self._html = HTML(owner=self)

    @property
    def name(self):
        return "test Neopixel segments"

    @property
    def hardware(self):
        return self.owner.hardware

    # def open(self, **kwargs):
        # if self._is_open:
            # return
        # self.hardware.connect()
        # self.owner.opened = self
        # self._is_open = True
        
        # for male in self.hardware.males:
            # for segment in male.segments:
                # segment.set_test_default()
        
        # for female in self.hardware.females:
            # for segment in female.segments:
                # segment.set_test_default()

    # def close(self, **kwargs):
        # if not self._is_open:
            # return
        # self.hardware.close()
        # self._is_open = False
        # self.owner.opened = None
            
        # self._add_html_start()


    # def stop(self, **kwarg):
        # if self.is_started:
            # for female in self.hardware.females:
                # female.neopixel.off()
            # for male in self.hardware.males:
                # male.body_neopixel.ring.off()
                # male.body_neopixel.drive.off()
        # ThreadElement.stop(self)

    # def _add_html_start(self):
        # doc, tag, text = self.html_doc.tagtext()
        # with tag("form", method="post"):

            # with tag("button", name="action", value="hardware/test_led_communication"):
                # text(f"Start.")

            # self.hardware.actions["hardware/test_led_communication"] = self.start            
            
        # self._write_html_action(value="hardware/test_led_communication/close", label="close", func=self.close)

    # def _add_html_stop(self):
        # doc, tag, text = self.html_doc.tagtext()
        # with tag("form", method="post"):
            # with tag("div"):
                # text(f"All LEDs should be on.")

            # with tag("button", name="action", value="hardware/test_led_communication/stop"):
                # text(f"Stop.")

            # self.hardware.actions["hardware/test_led_communication/stop"] = self.stop



class HTML(HtmlItem):
    
        
    def _call_unsafe(self,):          
        doc, tag, text = self.doc.tagtext()       
        for neopixel in self.owner.hardware.neopixels:
            with tag("h4"):
                text(f"{neopixel.body.name}/{neopixel.name}")   
                neopixel.html()

    @property
    def name(self):
        return "HTML"