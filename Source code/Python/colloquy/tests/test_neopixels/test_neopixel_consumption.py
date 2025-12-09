from server.html_element import HTMLElement

class TestNeopixelConsumption(HTMLElement):

    def __init__(self, owner):
        HTMLElement.__init__(self, owner)
        self._is_started = False
        self._is_open = False
        self.name = "test Neopixel consumption"

    # @property
    # def hardware(self):
        # return self.owner.hardware

    @property
    def is_started(self):
        return self._is_started

    @property
    def is_open(self):
        return self._is_open

    def open(self, **kwargs):
        if self._is_open:
            return
        self.hardware.connect()
        self.owner.opened = self
        # self._actions = {}
        self._is_open = True

    def close(self, **kwargs):
        if not self._is_open:
            return
        self.hardware.close()
        self._is_open = False
        self.owner.opened = None

    def write_html(self):
        doc, tag, text = self.html_doc.tagtext()
        
        if not self.is_open:
            self._write_html_open()
            return
            
        # if self.hardware.is_started:
        if self.is_started:
            self._add_html_title()
            self._add_html_stop()
            return
        

        self._add_html_title()
        self._add_html_start()
    
    def _write_html_open(self):
        doc, tag, text = self.html_doc.tagtext()
        self._write_html_action(value="hardware/tests/consumption/open", label=self.name, func=self.open)

    def _start(self, **kwargs):
        self._is_started = True
        
        brightness = 255
        color = dict(red=254, green=254, blue=254, white=254)
        
        for female in self.hardware.females:
            config = dict(
                brightness = brightness,
                **color,
                )
            female.neopixel.configure(**config)
            female.neopixel.on()
        for male in self.hardware.males:
            #brightness = 255
            #color = dict(red=0, green=0, blue=0, white=255)
            config = dict(
                brightness = brightness,
                **color,
                )
            male.body_neopixel.ring.configure(**config)
            male.body_neopixel.drive.configure(**config)
            male.body_neopixel.ring.on()
            male.body_neopixel.drive.on()



    def _stop(self, **kwarg):
        for female in self.hardware.females:
            female.neopixel.off()
        for male in self.hardware.males:
            male.body_neopixel.ring.off()
            male.body_neopixel.drive.off()
        self._is_started = False

    def _add_html_title(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("h3"):
            text(self.name.title())
        with tag("div"):
            text("Light up all the LED for measuring power consumption.")

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):

            with tag("button", name="action", value="hardware/test_led_consumption"):
                text(f"Start.")

            self.hardware.actions["hardware/test_led_consumption"] = self._start            
            
        self._write_html_action(value="hardware/test_led_consumption/close", label="close", func=self.close)

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("div"):
                text(f"All LEDs should be on.")

            with tag("button", name="action", value="hardware/test_led_consumption/stop"):
                text(f"Stop.")

            self.hardware.actions["hardware/test_led_consumption/stop"] = self._stop