
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

    def __hash__(self):
        return id(self)

    def write_html(self):
        raise NotImplementedError("""Example:
doc, tag, text = self._owner._doc.tagtext()
with tag("form", action="", method="post"):
    with tag("button", type="submit", name="command", value=self.name):
        text(self.name)
        """)

class BarMoveToPositionAndWait(Command):

    def __init__(self, owner, position, actors):
        self.position = position
        self.actors = actors
        Command.__init__(self, owner, name=f"bar/move to interaction between {self.actors.male.name} and {self.actors.female.name}")

    def __call__(self, **kwargs):
        position = int(kwargs["position"][0])
        self._owner.colloquy.bar.move_and_wait(self.position)
        # raise NotImplementedError
        yield "Finish moving the bar."

    def write_html(self):
        doc, tag, text = self._owner._doc.tagtext()
        colloquy = self._owner.colloquy
        position = round(self.position)
        with tag("form", action="", method="post"):
            with tag("input", type="number", name="position", value=position, step="1"):
                pass
            with tag("button", type="submit", name="command", value=self.name):
                text(self.name)

class BarMoveToOriginAndWait(Command):

    def __init__(self, owner):
        Command.__init__(self, owner, name=f"bar/move to origin")

    def __call__(self, **kwargs):
        yield f"Moving the bar to origin..."
        colloquy = self._owner.colloquy
        colloquy.bar.turn_to_origin_position()
        colloquy.bar.dxl.wait_for_servo()
        # raise NotImplementedError
        yield f"Finish moving the bar."

    def write_html(self):
        doc, tag, text = self._owner._doc.tagtext()
        colloquy = self._owner.colloquy
        position = colloquy.bar.dxl_origin
        with tag("form", action="", method="post"):
            with tag("input", type="number", name="position", value=position, disabled="True"):
                pass
            with tag("button", type="submit", name="command", value=self.name):
                text(self.name)

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
        colloquy = self._owner.colloquy
        position = self.body.dxl_origin
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
        colloquy = self._owner.colloquy
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
        colloquy = self._owner.colloquy
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
        self._owner.colloquy.bar.move_and_wait(position)
        # raise NotImplementedError
        yield "Finish moving the bar."

    def write_html(self):
        doc, tag, text = self._owner._doc.tagtext()
        colloquy = self._owner.colloquy
        position = round(colloquy.bar.position)
        with tag("form", action="", method="post"):
            with tag("input", type="number", name="position", value=position, step="1"):
                pass
            with tag("button", type="submit", name="command", value=self.name):
                text(self.name)