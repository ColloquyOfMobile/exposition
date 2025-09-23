from colloquy.neopixel import Neopixel
from pathlib import Path
from threading import Event

class UpRing(Neopixel):

    def __init__(self, owner, name):
        Neopixel.__init__(self, owner=owner, name=name)
        owner.segments.append(self)

    def write_html(self, ui_context = None):
        doc, tag, text = self.html_doc.tagtext()
        self._ui_context = ui_context
        
        self._write_html_configure()
        
        if self.state:
            self._write_html_action(value=f"hardware/{self.owner.name}/{self.name}/off", label=f"{self.name} off", func=self.off)
            return
        
        self._write_html_action(value=f"hardware/{self.owner.name}/{self.name}/on", label=f"{self.name} on", func=self.on)
    
    def _write_html_configure(self):
        doc, tag, text = self.html_doc.tagtext()
        config = self.configuration
        
        with tag("form", method="post"): 
            self._write_html_brightness()
            self._write_html_white()
            self._write_html_rgb()
            
            value = f"hardware/{self.owner.name}/{self.name}/color"
            with tag("button", name="action", value=value):
                text("configure")
            self.actions[value] = self._configure_from_html
    
    def _write_html_rgb(self):
        doc, tag, text = self.html_doc.tagtext()
        config = self.configuration

        red = config["red"]
        green = config["green"]
        blue = config["blue"]
            
        doc.stag("input", type="color", name="hex_rgb", value=self.rgb_to_hex(red, green, blue))
        
    
    def _write_html_brightness(self):
        doc, tag, text = self.html_doc.tagtext()
        config = self.configuration
        
        with tag("div"):            
            name = "brightness"
            with tag("label"):
                text(f"{name} : ")
            doc.stag("input", type="number", name=name, value=config[name], max=255, min=0, step=1)
    
    def _write_html_white(self):
        doc, tag, text = self.html_doc.tagtext()
        config = self.configuration
        
        with tag("div"):
            name = "white"
            with tag("label"):
                text(f"{name} : ")
            doc.stag("input", type="number", name=name, value=config[name], max=255, min=0, step=1)       
        
    def _configure_from_html(self, **kwargs):
        hex_color = kwargs["hex_rgb"][0]
        (red, green, blue) = self.hex_to_rgb(hex_color)
        white = int(kwargs["white"][0])
        brightness = int(kwargs["brightness"][0])
        
        self.configure(red, green, blue, white, brightness)
        
        raise NotImplementedError(f"{kwargs=}")

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
        # self._request_path = self._path.relative_to(self.hardware.path).as_posix()
        # self.arduino_manager = owner.arduino_manager
        # self._on_off_state = None
        # self.red = 0
        # self.green = 0
        # self.blue = 0
        # self.white = 0
        # self.brightness = 0

    # @property
    # def state(self):
        # return self._on_off_state

    # @property
    # def configuration(self):
        # return {
            # "red": self.red,
            # "green": self.green,
            # "blue": self.blue,
            # "white": self.white,
            # "brightness": self.brightness,
        # }

    # def open(self):
        # self.off()

    # def configure(self, red, green, blue, white, brightness):
        # self.red = red
        # self.green = green
        # self.blue = blue
        # self.white = white
        # self.brightness = brightness
        # self._update()

    # def _update(self):
        # if not self._on_off_state:
            # return
        # # path = f"{self._owner.name}/neopixel"
        # data = dict(
            # r = self.red,
            # g = self.green,
            # b = self.blue,
            # w = self.white,
            # brightness = self.brightness)
        # self.arduino_manager.send(self._request_path, **data)

    # def on(self):
        # self._on_off_state = True
        # self._update()

    # def off(self):
        # # path = f"{self._owner.name}/neopixel"
        # data = dict(
            # r = 0,
            # g = 0,
            # b = 0,
            # w = 0,
            # brightness = 0,)
        # self.arduino_manager.send(self._request_path, **data)
        # self._on_off_state = False

    # def toggle(self):
        # if self._on_off_state is None:
            # self.on()
            # return

        # if self._on_off_state:
            # self.off()
            # return

        # if not self._on_off_state:
            # self.on()
            # return

    # def set(self, value):
        # if value:
            # self.on()
        # else:
            # self.off()