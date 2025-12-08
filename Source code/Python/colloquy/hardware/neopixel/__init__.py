# from colloquy.wsgi.root.html_item import HtmlItem
from pathlib import Path
from colloquy.base import Base
from utils import CustomDoc
from threading import Event
from .toggle_on_off import ToggleOnOff
from .parameter import Parameter
from .brightness import Brightness
from .html import HTML

class Neopixel(Base):

    def __init__(self, owner, name):
        self._name = name
        super().__init__(owner=owner)
        self._is_open = False
        
        self._html = HTML(owner=self)
        
        self._toggle_on_off = ToggleOnOff(owner=self)
        
        self[self._toggle_on_off.name] = self._toggle_on_off        
        
        self._arduino = owner.arduino
        self._on_off_state = None
        
        self._red = Parameter(owner=self, name="red")
        self._green = Parameter(owner=self, name="green")
        self._blue = Parameter(owner=self, name="blue")
        
        self._white = Parameter(owner=self, name="white")
        self._brightness = Brightness(owner=self, name="brightness")
        
        self[self.white.name] = self.white        
        self[self.brightness.name] = self.brightness
        self[self._red.name] = self._red
        self[self._green.name] = self._green
        self[self._blue.name] = self._blue
        
        self["open"] = self.open
        self["close"] = self.close

    def __call__(self, request):
        request = Path(request)
        if not request.parts:
            raise NotImplementedError
            
        key, *leftover = request.parts
        
        if key in self:
            self[key](request="/".join(leftover))
            return
            
        raise NotImplementedError(f"{key=}, {leftover=}, in {self=}")  

    @property
    def colloquy(self):
        return self.owner.colloquy
        
    @property
    def workspace(self):
        return self.colloquy.server.wsgi.root.body.workspace
        
    @property
    def is_open(self):
        return self._is_open   

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
            "red": self.red.value,
            "green": self.green.value,
            "blue": self.blue.value,
            "white": self.white.value,
            "brightness": self.brightness.value,
        }
    
    @property
    def html(self):
        return self._html
    
    @property
    def brightness(self):
        return self._brightness
    
    @property
    def white(self):
        return self._white
    
    @property
    def red(self):
        return self._red
    
    @property
    def green(self):
        return self._green
    
    @property
    def blue(self):
        return self._blue
        
    @property
    def color(self):
        return dict(
            red=self.red.value, 
            green=self.green.value, 
            blue=self.blue.value, 
            white=self.white.value
            )

    @color.setter
    def color(self, value):
        self.red.value = value["red"]
        self.green.value = value["green"]
        self.blue.value = value["blue"]
        self.white.value = value["white"]
        self.update()

    def open(self, request=None):
        if self.workspace.opened is not None:
            self.workspace.opened.close()
        self._is_open = True
        self.workspace.opened = self

    def close(self, request=None):
        self._is_open = False
        self.workspace.opened = None

    def configure(self, red, green, blue, white, brightness):
        self.red.value = red
        self.green.value = green
        self.blue.value = blue
        self.white.value = white
        self.brightness.value = brightness
        self.update()

    def update(self):
        if not self._on_off_state:
            return
        data = dict(
            r = self._adjust_brightness(self.red.value),
            g = self._adjust_brightness(self.green.value),
            b = self._adjust_brightness(self.blue.value),
            w = self._adjust_brightness(self.white.value)
            )
        self.arduino.send(self.arduino_path, **data)

    def on(self, **kwargs):
        self._on_off_state = True
        self.update()

    def off(self, **kwargs):
        data = dict(
            r = 0,
            g = 0,
            b = 0,
            w = 0,)
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
    
    def _adjust_brightness(self, value):
        return int((value * self.brightness.value) / 100)