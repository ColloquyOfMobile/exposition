from .commands import Command

class BodyToggleNeopixel(Command):

    def __init__(self, owner, body):
        self.body = body
        Command.__init__(self, owner, name=f"{body.name}/neopixel/toggle")

    def __call__(self, **kwargs):
        self.body.toggle_neopixel()
        yield f"Neopixel toggled for {self.body.name}."

    def write_html(self):
        doc, tag, text = self._owner._doc.tagtext()
        colloquy = self._owner.colloquy
        value = self.body.neopixel.state
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


class BodyConfigureNeopixel(Command):

    def __init__(self, owner, body):
        self.body = body
        Command.__init__(self, owner, name=f"{body.name}/neopixel/configure")

    def __call__(self, **kwargs):
        red = int(kwargs.get("red", [self.body.neopixel.red])[0])
        green = int(kwargs.get("green", [self.body.neopixel.green])[0])
        blue = int(kwargs.get("blue", [self.body.neopixel.blue])[0])
        white = int(kwargs.get("white", [self.body.neopixel.white])[0])
        brightness = int(kwargs.get("brightness", [self.body.neopixel.brightness])[0])
        self.body.neopixel.configure(red, green, blue, white, brightness)
        yield f"Neopixel configured for {self.body.name}."

    def write_html(self):
        doc, tag, text = self._owner._doc.tagtext()
        colloquy = self._owner.colloquy
        config = self.body.neopixel.configuration

        with tag("form", action="", method="post", style="display: flex;"):
            for name, value in config.items():
                id = f"neopixel/{name}"
                with tag("div"):
                    with tag("label", id=id):
                        text(name)

                    doc.stag("input", id=id, type="number", name=name, value=value, max=255, min=0, step=1)

            with tag("button", type="submit", name="command", value=self.name):
                text(self.name)