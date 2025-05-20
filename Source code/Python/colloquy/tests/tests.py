from server.html_element import HTMLElement



class Tests(HTMLElement):

    def __init__(self, owner):
        HTMLElement.__init__(self, owner)
        self._test1 = Test1(owner=self)

    @property
    def colloquy(self):
        return self.owner

    def add_html(self):
        doc, tag, text = self.html_doc.tagtext()
        self._test1.add_html()

class Test1(HTMLElement):

    def __init__(self, owner):
        HTMLElement.__init__(self, owner)
        self._interaction = self.colloquy.nearby_interactions[0]

    @property
    def colloquy(self):
        return self.owner.colloquy

    def add_html(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("h2"):
            text("Test when female wants to interact but the male doesn't hear.")

        if self.colloquy.nearby_interaction is None:
            self._add_html_start()
            return
        else:
            if not self.colloquy.nearby_interaction.is_started:
                self._add_html_start()
                return

        self._add_html_stop()

    def _start(self, **kwargs):

        interaction = self._interaction
        self.colloquy.bar.nearby_interaction = interaction

        interaction.female.drives.o_drive = 255
        interaction.female.drives.p_drive = 10
        interaction.female.neopixel.on()
        interaction.female.target_drive = interaction.female.drives.state

        interaction.male.drives.o_drive = 255
        interaction.male.drives.p_drive = 10
        interaction.male.body_neopixel.drive.on()

        interaction.male.microphone = False

        assert interaction.female.drives.is_frustated

        print(f"Move bar to interaction.")
        interaction.move_to_position_and_wait()

        interaction.male.search.start()
        interaction.start()

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):

            with tag("button", name="action", value="colloquy/test1"):
                text(f"Start.")

            self.colloquy.actions["colloquy/test1"] = self._start

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        male = self._interaction.male
        female = self._interaction.female
        with tag("form", method="post"):
            with tag("div"):
                text(f"Interacting between {male.name}-{female.name}!")

            with tag("button", name="action", value="colloquy/test1/stop"):
                text(f"Stop.")

            self.colloquy.actions["colloquy/test1/stop"] = self._interaction.stop