from .commands import Command

class ToggleNeopixel(Command):

    def __init__(self, owner, body, name):
        self.body = body
        Command.__init__(self, owner, name)

    @property
    def neopixel(self):
        raise NotImplementedError(f"for {self=}!")

    def __call__(self, **kwargs):
        self.neopixel.toggle()
        yield f"Neopixel '{self.neopixel.name}' toggled for {self.body.name}."

    def write_html(self):
        doc, tag, text = self._owner._doc.tagtext()
        colloquy = self._owner.colloquy
        value = self.neopixel.state
        if value is None:
            value = "unknown"
        if value is True:
            value = "On"
        if value is False:
            value = "Off"
        with tag("form", action="", method="post", style="display: flex; flex-wrap: wrap;"):
            with tag("input", name="state", value=value, disabled=True):
                pass
            with tag("button", type="submit", name="command", value=self.name):
                text(self.name)

class MaleToggleRingNeopixel(ToggleNeopixel):

    def __init__(self, owner, body):
        ToggleNeopixel.__init__(self, owner, body, name=f"{body.name}/body/ring/toggle")

    @property
    def neopixel(self):
        return self.body.body_neopixel.ring

class MaleToggleDriveNeopixel(ToggleNeopixel):

    def __init__(self, owner, body):
        ToggleNeopixel.__init__(self, owner, body, name=f"{body.name}/body/drive/toggle")

    @property
    def neopixel(self):
        return self.body.body_neopixel.drive


class MaleToggleUpRingNeopixel(ToggleNeopixel):

    def __init__(self, owner, body):
        ToggleNeopixel.__init__(self, owner, body, name=f"{body.name}/up_ring/toggle")

    @property
    def neopixel(self):
        return self.body.up_ring

class FemaleToggleNeopixel(ToggleNeopixel):

    def __init__(self, owner, body):
        ToggleNeopixel.__init__(self, owner, body, name=f"{body.name}/neopixel/toggle")

    @property
    def neopixel(self):
        return self.body.neopixel


class ConfigureNeopixel(Command):

    def __init__(self, owner, body, name):
        self.body = body
        Command.__init__(self, owner, name)

    @property
    def neopixel(self):
        raise NotImplementedError(f"for {self=}!")

    def __call__(self, **kwargs):
        hex_color = kwargs["hex_rgb"][0]
        (red, green, blue) = self.hex_to_rgb(hex_color)

        white = int(kwargs["white"][0])
        brightness = int(kwargs["brightness"][0])

        self.neopixel.configure(red, green, blue, white, brightness)

        yield f"Neopixel '{self.neopixel.name}' configured for {self.body.name}."

    def write_html(self):
        doc, tag, text = self._owner._doc.tagtext()
        colloquy = self._owner.colloquy
        config = self.neopixel.configuration

        with tag("form", action="", method="post", style="display: flex; flex-wrap: wrap;"):
            # for name, value in config.items():
                # with tag("div", style="display: flex; flex-direction: column;"):
            name = "brightness"
            id = f"{self.name}/{name}"
            with tag("label", id=id):
                text(name)

            doc.stag("input", id=id, type="number", name=name, value=config[name], max=255, min=0, step=1)

            name = "white"
            id = f"{self.name}/{name}"
            with tag("label", id=id):
                text(name)

            doc.stag("input", id=id, type="number", name=name, value=config[name], max=255, min=0, step=1)

            red = config["red"]
            green = config["green"]
            blue = config["blue"]

            doc.stag("input", type="color", name="hex_rgb", value=self.rgb_to_hex(red, green, blue))

            with tag("button", type="submit", name="command", value=self.name):
                text(self.name)

    def rgb_to_hex(self, red, green, blue):
        for value in (red, green, blue):
            assert 0 <= value <= 255
        return '#{:02X}{:02X}{:02X}'.format(red, green, blue)

    def hex_to_rgb(self, hex_value):
        hex_value = hex_value.lstrip('#')  # Retire le #
        if len(hex_value) != 6:
            raise ValueError("La valeur hexadécimale doit contenir exactement 6 caractères.")
        r = int(hex_value[0:2], 16)
        g = int(hex_value[2:4], 16)
        b = int(hex_value[4:6], 16)
        return (r, g, b)

class FemaleConfigureNeopixel(ConfigureNeopixel):

    def __init__(self, owner, body):
        ConfigureNeopixel.__init__(self, owner, body, name=f"{body.name}/neopixel/configure")

    @property
    def neopixel(self):
        return self.body.neopixel

class MaleConfigureUpRingNeopixel(ConfigureNeopixel):

    def __init__(self, owner, body):
        ConfigureNeopixel.__init__(self, owner, body, name=f"{body.name}/UpRing/configure")

    @property
    def neopixel(self):
        return self.body.up_ring

class MaleConfigureDriveNeopixel(ConfigureNeopixel):

    def __init__(self, owner, body):
        ConfigureNeopixel.__init__(self, owner, body, name=f"{body.name}/body/drive/configure")

    @property
    def neopixel(self):
        return self.body.body_neopixel.drive

class MaleConfigureRingNeopixel(ConfigureNeopixel):

    def __init__(self, owner, body):
        ConfigureNeopixel.__init__(self, owner, body, name=f"{body.name}/body/ring/configure")

    @property
    def neopixel(self):
        return self.body.body_neopixel.ring