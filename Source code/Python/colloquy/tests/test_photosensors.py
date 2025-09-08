from server.html_element import HTMLElement

class TestPhotosensors(HTMLElement):

    def __init__(self, owner):
        HTMLElement.__init__(self, owner)
        self._is_started = False
        self._is_open = False
        self.name = "test photosensors"
        # self.speaker_on = None

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def is_started(self):
        return self._is_started

    @property
    def is_open(self):
        return self._is_open

    def open(self, **kwargs):
        if self._is_open:
            return
        self.colloquy.connect()
        self.owner.opened = self
        self._is_open = True

    def close(self, **kwargs):
        if not self._is_open:
            return
        # raise NotImplementedError
        # if self.speaker_on is not None:
            # self.speaker_on.off()
        self.colloquy.close()
        self._is_open = False
        self.owner.opened = None

    def _start(self, **kwargs):
        raise NotImplementedError(f"{kwargs=}")

    def _stop(self, **kwargs):
        raise NotImplementedError(f"{kwargs=}")

    def write_html(self):
        doc, tag, text = self.html_doc.tagtext()
        
        if not self.is_open:
            self._write_html_open()
            return

        self._add_html_title()
        
        if self._is_started:
            self._write_html_action(value="colloquy/tests/photosensors/stop", label="stop", func=self._stop)
            return
        
            
        self._write_html_action(value="colloquy/tests/photosensors/close", label="close", func=self.close)
        
        self._write_html_action(value="colloquy/tests/photosensors/start", label="start", func=self._start)
        # print(f"{self.speaker_on=}")
        # if self.speaker_on is not None:
            # self.speaker_on.write_html(ui_context=self)
            # return 
        
        # for female in self.colloquy.females:
            # female.photosensors.write_html(ui_context=self)
    
    def _write_html_open(self):
        doc, tag, text = self.html_doc.tagtext()
        self._write_html_action(value="colloquy/tests/speaker/open", label=self.name, func=self.open)


    def _add_html_title(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("h3"):
            text(self.name.title())
        with tag("div"):
            text("Enable testing photosensors one by one.")

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("div"):
                text(f"All LEDs should be on.")

            with tag("button", name="action", value="colloquy/test_led_consumption/stop"):
                text(f"Stop.")

            self.colloquy.actions["colloquy/test_led_consumption/stop"] = self._stop