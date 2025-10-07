from colloquy.thread_element import ThreadElement

class TestNeopixelSegments(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name="test Neopixel segments")
        self._is_open = False

    @property
    def hardware(self):
        return self.owner.hardware

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
        

        self._add_html_title()            
            
        self._write_html_action(value=f"hardware/{self.name}/close", label="close", func=self.close)
        
        doc, tag, text = self.html_doc.tagtext()
        
        for male in self.hardware.males:
            with tag("h4"):
                text(male.name)
            for segment in male.segments:
                segment.set_test_default()
                segment.write_html()
        
        for female in self.hardware.females:
            with tag("h4"):
                text(female.name)
            for segment in female.segments:
                segment.set_test_default()
                segment.write_html()
            
            
        # self._add_html_start()
    
    def _write_html_open(self):
        doc, tag, text = self.html_doc.tagtext()
        self._write_html_action(value="hardware/tests/communication/open", label=self.name, func=self.open)


    # def stop(self, **kwarg):
        # if self.is_started:
            # for female in self.hardware.females:
                # female.neopixel.off()
            # for male in self.hardware.males:
                # male.body_neopixel.ring.off()
                # male.body_neopixel.drive.off()
        # ThreadElement.stop(self)

    def _add_html_title(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("h3"):
            text(self.name.title())
        with tag("div"):
            text("Enables controlling each LED segments.")

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