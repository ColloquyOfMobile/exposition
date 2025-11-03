# from colloquy.wsgi.root.body.action_item import ActionItem
from colloquy.wsgi.root.body.workspace.item import Item, Action
from colloquy.wsgi.root.body.command import Command, HTML as _HTML


class SetWhite(Command):
    
    def __init__(self, owner):
        Command.__init__(self, owner)
        self._action = Action(owner=self)
        self._html = HTML(owner=self)
    
    def __call__(self):
        value = self.post_data["value"][0]
        color = {
        "red": self.owner.red,
        "green": self.owner.green,
        "blue": self.owner.blue,
        "white": value,
        }
        self.owner.color = color

    @property
    def name(self):
        return "set white"

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
        value = self.owner.owner.white
            
        with tag("form", method="post", style="display: flex; "):
        
            with tag("label", style="margin-left: 1ch; margin-right: 1ch;"):
                text("white")
                
            doc.stag("input", type="number", name="value", value=value)
        
            with tag("button", name="action", value=self.owner.action.value):
                text("set")
            
    def rgb_to_hex(self, red, green, blue):
        for value in (red, green, blue):
            assert 0 <= value <= 255
        return '#{:02X}{:02X}{:02X}'.format(red, green, blue)