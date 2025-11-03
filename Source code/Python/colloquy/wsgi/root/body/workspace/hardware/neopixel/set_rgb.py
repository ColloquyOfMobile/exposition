# from colloquy.wsgi.root.body.action_item import ActionItem
from colloquy.wsgi.root.body.workspace.item import Item, Action
from colloquy.wsgi.root.body.command import Command, HTML as _HTML


class SetRGB(Command):
    
    def __init__(self, owner):
        Command.__init__(self, owner)
        self._action = Action(owner=self)
        self._html = HTML(owner=self)
    
    def __call__(self):
        hex_rgb = self.post_data["hex_rgb"][0]
        rgb = self.hex_to_rgb(hex_rgb)
        color = {
        "red": rgb[0],
        "green": rgb[1],
        "blue": rgb[2],
        "white": self.owner.white,
        }
        self.owner.color = color

    @property
    def name(self):
        return "set rgb"

    def hex_to_rgb(self, hex_value):
        hex_value = hex_value.lstrip('#')  # Retire le #
        if len(hex_value) != 6:
            raise ValueError("La valeur hexadécimale doit contenir exactement 6 caractères.")
        r = int(hex_value[0:2], 16)
        g = int(hex_value[2:4], 16)
        b = int(hex_value[4:6], 16)
        return (r, g, b)

class HTML(_HTML):

    def __call__(self):
        doc, tag, text = self.doc.tagtext()
        config = self.owner.owner.configuration

        red = config["red"]
        green = config["green"]
        blue = config["blue"]
            
        with tag("form", method="post", style="display: flex; "):
            doc.stag("input", type="color", name="hex_rgb", value=self.rgb_to_hex(red, green, blue))
        
            with tag("button", name="action", value=self.owner.action.value):
                text("set")
            
    def rgb_to_hex(self, red, green, blue):
        for value in (red, green, blue):
            assert 0 <= value <= 255
        return '#{:02X}{:02X}{:02X}'.format(red, green, blue)