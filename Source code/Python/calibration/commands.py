
class Command:

    def __init__(self, owner, name):
        self._owner = owner
        self.name = name

    def __call__(self, inst):
        raise NotImplementedError

    def __eq__(self, other):
        return other.name == self.name

    def __lt__(self, other):
        if not isinstance(other, Command):
            return NotImplemented
        return self.name < other.name

    def write_html(self):
        raise NotImplementedError("""Example:
doc, tag, text = self._owner._doc.tagtext()
with tag("form", action="", method="post"):
    with tag("button", type="submit", name="command", value=self.name):
        text(self.name)
        """)

class BodyMoveToOriginAndWait(Command):

    def __init__(self, owner, body):
        self.body = body
        Command.__init__(self, owner, name=f"{body.name}/move to origin")

    def __call__(self, **kwargs):
        yield f"Moving the {self.body.name} to origin..."
        # position = int(kwargs["position"][0])
        self.body.turn_to_origin_position()
        self.body.dxl.wait_for_servo()
        # raise NotImplementedError
        yield f"Finish moving the {self.body.name}."

    def write_html(self):
        doc, tag, text = self._owner._doc.tagtext()
        colloquy_driver = self._owner.colloquy_driver
        position = round(self.body.position)
        with tag("form", action="", method="post"):
            with tag("input", type="number", name="position", value=position, disabled="True"):
                pass
            with tag("button", type="submit", name="command", value=self.name):
                text(self.name)


class BodyToggleSpeaker(Command):

    def __init__(self, owner, body):
        self.body = body
        Command.__init__(self, owner, name=f"{body.name}/toggle speaker")

    def __call__(self, **kwargs):
        self.body.toggle_speaker()
        yield f"Speaker toggled for {self.body.name}."

    def write_html(self):
        doc, tag, text = self._owner._doc.tagtext()
        colloquy_driver = self._owner.colloquy_driver
        value = self.body.speaker_state
        if value is None:
            value = "unknown"
        if value is True:
            value = "On"
        if value is False:
            value = "Off"
        with tag("form", action="", method="post"):
            with tag("input", name="state", value=value, disabled=True):
                pass
            with tag("button", type="submit", name="command", value=self.name):
                text(self.name)

class BodyToggleNeopixel(Command):

    def __init__(self, owner, body):
        self.body = body
        Command.__init__(self, owner, name=f"{body.name}/toggle neopixel")

    def __call__(self, **kwargs):
        # position = int(kwargs["position"][0])
        self.body.toggle_neopixel()
        # raise NotImplementedError
        yield f"Neopixel toggled for {self.body.name}."

    def write_html(self):
        doc, tag, text = self._owner._doc.tagtext()
        colloquy_driver = self._owner.colloquy_driver
        value = self.body.neopixel_state
        if value is None:
            value = "unknown"
        if value is True:
            value = "On"
        if value is False:
            value = "Off"
        with tag("form", action="", method="post"):
            with tag("input", name="state", value=value, disabled=True):
                pass
            with tag("button", type="submit", name="command", value=self.name):
                text(self.name)

class BodyMoveAndWait(Command):

    def __init__(self, owner, body):
        self.body = body
        Command.__init__(self, owner, name=f"{body.name}/move and wait")

    def __call__(self, **kwargs):
        yield f"Moving the {self.body.name}..."
        position = int(kwargs["position"][0])
        self.body.move_and_wait(position)
        # raise NotImplementedError
        yield f"Finish moving the {self.body.name}."

    def write_html(self):
        doc, tag, text = self._owner._doc.tagtext()
        colloquy_driver = self._owner.colloquy_driver
        position = round(self.body.position)
        with tag("form", action="", method="post"):
            with tag("input", type="number", name="position", value=position, step="1"):
                pass
            with tag("button", type="submit", name="command", value=self.name):
                text(self.name)

class BarMoveAndWait(Command):

    def __init__(self, owner):
        Command.__init__(self, owner, name="bar/move and wait")

    def __call__(self, **kwargs):
        position = int(kwargs["position"][0])
        self._owner.colloquy_driver.bar.move_and_wait(position)
        # raise NotImplementedError
        yield "Finish moving the bar."

    def write_html(self):
        doc, tag, text = self._owner._doc.tagtext()
        colloquy_driver = self._owner.colloquy_driver
        position = round(colloquy_driver.bar.position)
        with tag("form", action="", method="post"):
            with tag("input", type="number", name="position", value=position, step="1"):
                pass
            with tag("button", type="submit", name="command", value=self.name):
                text(self.name)