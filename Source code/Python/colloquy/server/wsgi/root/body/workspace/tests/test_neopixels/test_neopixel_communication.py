from colloquy.thread_element import ThreadElement

class TestNeopixelCommunication(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name="test Neopixel communication")
        # self._is_started = False
        self._is_open = False
        self._color_index = 0
        self._colors = [
            dict(red=255, green=255, blue=255, white=0),
            dict(red=0, green=0, blue=0, white=255),
            dict(red=0, green=0, blue=255, white=0),
            dict(red=255, green=0, blue=0, white=0),
            dict(red=0, green=255, blue=0, white=0),
            dict(red=0, green=255, blue=255, white=0),
            dict(red=255, green=0, blue=255, white=0),
            dict(red=255, green=255, blue=0, white=0),
        ]

    # @property
    # def hardware(self):
        # return self.owner.hardware


    @property
    def is_open(self):
        return self._is_open

    def open(self, **kwargs):
        if self._is_open:
            return
        self.hardware.connect()
        self.owner.opened = self
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
            
        if self.is_started:
            self._add_html_title()
            self._add_html_stop()
            return
        

        self._add_html_title()
        self._add_html_start()
    
    def _write_html_open(self):
        doc, tag, text = self.html_doc.tagtext()
        self._write_html_action(value="hardware/tests/communication/open", label=self.name, func=self.open)

    def _loop(self):
        self._is_started = True
        
        brightness = 255
        index = self._color_index % len(self._colors)
        self._color_index += 1
        color = self._colors[index]
        
        for female in self.hardware.females:
            config = dict(
                brightness = brightness,
                **color,
                )
            female.neopixel.configure(**config)
            female.neopixel.on()
            
        for male in self.hardware.males:
            config = dict(
                brightness = brightness,
                **color,
                )
            male.body_neopixel.ring.configure(**config)
            male.body_neopixel.drive.configure(**config)
            male.body_neopixel.ring.on()
            male.body_neopixel.drive.on()


    def stop(self, **kwarg):
        if self.is_started:
            for female in self.hardware.females:
                female.neopixel.off()
            for male in self.hardware.males:
                male.body_neopixel.ring.off()
                male.body_neopixel.drive.off()
        ThreadElement.stop(self)

    def _add_html_title(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("h3"):
            text(self.name.title())
        with tag("div"):
            text("Light up all the LED to test communication.")

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):

            with tag("button", name="action", value="hardware/test_led_communication"):
                text(f"Start.")

            self.hardware.actions["hardware/test_led_communication"] = self.start            
            
        self._write_html_action(value="hardware/test_led_communication/close", label="close", func=self.close)

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("div"):
                text(f"All LEDs should be on.")

            with tag("button", name="action", value="hardware/test_led_communication/stop"):
                text(f"Stop.")

            self.hardware.actions["hardware/test_led_communication/stop"] = self.stop