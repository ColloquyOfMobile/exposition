from server.html_element import HTMLElement

class TestNeopixelConsumption(HTMLElement):

    def __init__(self, owner):
        HTMLElement.__init__(self, owner)
        self._is_started = False
        self._interaction = None

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def is_started(self):
        return self._is_started

    def add_html(self):
        doc, tag, text = self.html_doc.tagtext()
        if self.colloquy.is_started:
            if self.is_started:
                self._add_html_title()
                self._add_html_stop()
                return
            return

        self._add_html_title()

        if self.colloquy.interaction is None:
            self._add_html_start()
            return
        else:
            if not self.colloquy.interaction.is_started:
                self._add_html_start()
                return

    def _start(self, **kwargs):
        self._is_started = True
        
        brightness = 255
        color = dict(red=254, green=254, blue=254, white=254)
        
        for female in self.colloquy.females:
            config = dict(
                brightness = brightness,
                **color,
                )
            female.neopixel.configure(**config)
            female.neopixel.on()
        for male in self.colloquy.males:
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
        for female in self.colloquy.females:
            female.neopixel.off()
        for male in self.colloquy.males:
            male.body_neopixel.ring.off()
            male.body_neopixel.drive.off()
        self._is_started = False

    def _add_html_title(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("h3"):
            text("Test Neopixel consumption.")
        with tag("div"):
            text("Light up all the LED for measuring power consumption.")

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):

            with tag("button", name="action", value="colloquy/test_led_consumption"):
                text(f"Start.")

            self.colloquy.actions["colloquy/test_led_consumption"] = self._start

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("div"):
                text(f"All LEDs should be on.")

            with tag("button", name="action", value="colloquy/test_led_consumption/stop"):
                text(f"Stop.")

            self.colloquy.actions["colloquy/test_led_consumption/stop"] = self._stop