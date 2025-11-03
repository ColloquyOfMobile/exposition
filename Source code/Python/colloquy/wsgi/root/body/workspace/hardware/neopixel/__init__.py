from colloquy.wsgi.root.html_item import HtmlItem
from pathlib import Path
from colloquy.wsgi.root.body.workspace.hardware.item import Item, HTML as _HTML
from threading import Event
from .toggle_on_off import ToggleOnOff
from .set_rgb import SetRGB
from .set_white import SetWhite
from .set_brightness import SetBrightness

class Neopixel(Item):

    def __init__(self, owner, name):
        self._name = name
        Item.__init__(self, owner=owner)
        self._html = HTML(owner=self)
        
        self._toggle_on_off = ToggleOnOff(owner=self)
        self._set_rgb = SetRGB(owner=self)
        self._set_white = SetWhite(owner=self)
        self._set_brightness = SetBrightness(owner=self)
        
        self._arduino = owner.arduino
        self._on_off_state = None
        self.red = 0
        self.green = 0
        self.blue = 0
        self.white = 0
        self._brightness = 0

    @property
    def arduino_path(self):
        raise NotImplementedError(f"{self=}")        

    @property
    def body(self):
        if self._body is None:
            raise NotImplementedError(f"{self=}")
        return self._body        

    @property
    def toggle_on_off(self):
        return self._toggle_on_off             

    @property
    def set_rgb(self):
        return self._set_rgb                 

    @property
    def set_brightness(self):
        return self._set_brightness            

    @property
    def set_white(self):
        return self._set_white   
        
    @property
    def arduino(self):
        return self._arduino

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._on_off_state

    @property
    def configuration(self):
        return {
            "red": self.red,
            "green": self.green,
            "blue": self.blue,
            "white": self.white,
            "brightness": self.brightness,
        }
    
    @property
    def brightness(self):
        return self._brightness
    
    @brightness.setter
    def brightness(self, value):
        self._brightness = value
        self._update()

    @property
    def color(self):
        return dict(red=self.red, green=self.green, blue=self.blue, white=self.white)

    @color.setter
    def color(self, value):
        self.red = value["red"]
        self.green = value["green"]
        self.blue = value["blue"]
        self.white = value["white"]
        self._update()

    def open(self):
        self.off()

    def configure(self, red, green, blue, white, brightness):
        self.red = red
        self.green = green
        self.blue = blue
        self.white = white
        self.brightness = brightness
        self._update()

    def _update(self):
        if not self._on_off_state:
            return
        # path = f"{self._owner.name}/neopixel"
        data = dict(
            r = self.red,
            g = self.green,
            b = self.blue,
            w = self.white,
            brightness = self.brightness)
        self.arduino.send(self.arduino_path, **data)

    def on(self, **kwargs):
        self._on_off_state = True
        self._update()

    def off(self, **kwargs):
        # path = f"{self._owner.name}/neopixel"
        data = dict(
            r = 0,
            g = 0,
            b = 0,
            w = 0,
            brightness = 0,)
        self.arduino.send(self.arduino_path, **data)
        self._on_off_state = False

    def toggle(self):
        if self._on_off_state is None:
            self.on()
            return

        if self._on_off_state:
            self.off()
            return

        if not self._on_off_state:
            self.on()
            return

    def set(self, value):
        if value:
            self.on()
        else:
            self.off()
            
    # def rgb_to_hex(self, red, green, blue):
        # for value in (red, green, blue):
            # assert 0 <= value <= 255
        # return '#{:02X}{:02X}{:02X}'.format(red, green, blue)

    def hex_to_rgb(self, hex_value):
        hex_value = hex_value.lstrip('#')  # Retire le #
        if len(hex_value) != 6:
            raise ValueError("La valeur hexadécimale doit contenir exactement 6 caractères.")
        r = int(hex_value[0:2], 16)
        g = int(hex_value[2:4], 16)
        b = int(hex_value[4:6], 16)
        return (r, g, b)

    def write_html(self, ui_context = None):
        doc, tag, text = self.html_doc.tagtext()
        
        self._write_html_configure()
        
        if self.state:
            self._write_html_action(value=f"{self.path.as_posix()}/off", label=f"{self.name} off", func=self.off)
            return
        
        self._write_html_action(value=f"{self.path.as_posix()}/on", label=f"{self.name} on", func=self.on)
        doc.stag("hr")
    
    def _write_html_configure(self):
        doc, tag, text = self.html_doc.tagtext()
        config = self.configuration
        
        with tag("div"):
            with tag("div"):
                with tag("strong"):
                    text(self.name)
            with tag("form", method="post"): 
                self._write_html_brightness()
                self._write_html_white()
                self._write_html_rgb()
                
                value = f"{self.path.as_posix()}/color"
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
        

class HTML(_HTML):
    
        
    def _call_unsafe(self,):          
        doc, tag, text = self.doc.tagtext()        
        with tag("h4"):
            text(f"{self.owner.body.name}/{self.owner.name}")  
        self.owner.toggle_on_off.html()
        self.owner.set_rgb.html()
        self.owner.set_white.html()
        self.owner.set_brightness.html()
        # if self.owner.state:
            # raise NotImplementedError


# class Action(ActionItem):
    
    # def __call__(self, **kwargs):
        # hex_color = kwargs["hex_rgb"][0]
        # (red, green, blue) = self.hex_to_rgb(hex_color)
        # white = int(kwargs["white"][0])
        # brightness = int(kwargs["brightness"][0])
        
        # self.configure(red, green, blue, white, brightness)
