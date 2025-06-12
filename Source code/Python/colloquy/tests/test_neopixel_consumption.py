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
        for female in self.females:
            brightness = 255
            color = female.drive.puce
            config = dict(
                brightness = brightness,
                **color,
                )
            female.neopixel.configure(**config)
        for male in self.males:
            raise NotImplementedError("Light up the male Neopixel.")
            male.neopixel
        

    def _stop(self):
        self._interaction.stop()
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
        male = self._interaction.male
        female = self._interaction.female
        with tag("form", method="post"):
            with tag("div"):
                text(f"Interacting between {male.name}-{female.name}!")

            with tag("button", name="action", value="colloquy/test_led_consumption/stop"):
                text(f"Stop.")

            self.colloquy.actions["colloquy/test_led_consumption/stop"] = self._stop