from server.html_element import HTMLElement

class Test1(HTMLElement):

    def __init__(self, owner):
        HTMLElement.__init__(self, owner)
        self._is_started = False
        self._interaction = None

    # @property
    # def hardware(self):
        # return self.owner.hardware

    @property
    def is_started(self):
        return self._is_started

    def add_html(self):
        doc, tag, text = self.html_doc.tagtext()
        if self.hardware.is_started:
            if self.is_started:
                self._add_html_title()
                self._add_html_stop()
                return
            return

        self._add_html_title()

        if self.hardware.interaction is None:
            self._add_html_start()
            return
        else:
            if not self.hardware.interaction.is_started:
                self._add_html_start()
                return

    def _start(self, **kwargs):
        self._is_started = True
        self._interaction = interaction = self.hardware.interactions[0]
        self.hardware.bar.interaction = interaction

        interaction.female.drives.o_drive = 255
        interaction.female.drives.p_drive = 10
        interaction.female.neopixel.on()
        interaction.female.target_drive = interaction.female.drives.state

        interaction.male.drives.o_drive = 255
        interaction.male.drives.p_drive = 10
        interaction.male.body_neopixel.drive.on()

        interaction.male.microphone.is_plugged = False

        assert interaction.female.drives.is_frustated

        print(f"Move bar to interaction.")
        interaction.move_to_position_and_wait()

        interaction.male.search.start()
        interaction.start()

    def _stop(self):
        self._interaction.stop()
        self._is_started = False

    def _add_html_title(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("h3"):
            text("Test1.")
        with tag("div"):
            text("Test when female wants to interact but the male doesn't hear.")

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):

            with tag("button", name="action", value="hardware/test1"):
                text(f"Start.")

            self.hardware.actions["hardware/test1"] = self._start

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        male = self._interaction.male
        female = self._interaction.female
        with tag("form", method="post"):
            with tag("div"):
                text(f"Interacting between {male.name}-{female.name}!")

            with tag("button", name="action", value="hardware/test1/stop"):
                text(f"Stop.")

            self.hardware.actions["hardware/test1/stop"] = self._stop