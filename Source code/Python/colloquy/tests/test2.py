from .test1 import Test1

class Test2(Test1):


    def _start(self, **kwargs):

        interaction = self._interaction
        self.colloquy.bar.interaction = interaction

        interaction.female.drives.o_drive = 255
        interaction.female.drives.p_drive = 10
        interaction.female.neopixel.on()
        # interaction.female.target_drive = interaction.female.drives.state

        interaction.male.drives.o_drive = 255
        interaction.male.drives.p_drive = 10
        interaction.male.body_neopixel.drive.on()
        # interaction.male.target_drive = interaction.male.drives.state
        assert interaction.female.drives.state == interaction.male.drives.state
        interaction.target_drive = interaction.female.drives.state

        interaction.male.microphone.is_plugged = True

        assert interaction.female.drives.is_frustated

        print(f"Move bar to interaction.")
        interaction.move_to_position_and_wait()

        interaction.male.drives.start()
        interaction.start()

    def _add_html_title(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("h3"):
            text("Test2.")
        with tag("div"):
            text("Test when female and the male interacts.")

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):

            with tag("button", name="action", value="colloquy/test2"):
                text(f"Start.")

            self.colloquy.actions["colloquy/test2"] = self._start

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        male = self._interaction.male
        female = self._interaction.female
        with tag("form", method="post"):
            with tag("div"):
                text(f"Interacting between {male.name}-{female.name}!")

            with tag("button", name="action", value="colloquy/test2/stop"):
                text(f"Stop.")

            self.colloquy.actions["colloquy/test2/stop"] = self._stop