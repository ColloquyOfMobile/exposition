from .thread_driver import ThreadDriver
from pathlib import Path
from threading import Event

class NeopixelDriver(ThreadDriver):

    def __init__(self, owner, arduino_manager):
        self._owner = owner
        self.arduino_manager = arduino_manager
        self._on_off_state = None
        self.red = 0
        self.green = 0
        self.blue = 0
        self.white = 0
        self.brightness = 0
        self.off()

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
        path = f"{self._owner.name}/neopixel"
        data = dict(
            r = self.red,
            g = self.green,
            b = self.blue,
            w = self.white,
            brightness = self.brightness)
        self.arduino_manager.send(path, **data)

    def on(self):
        self._on_off_state = True
        self._update()

    def off(self):
        path = f"{self._owner.name}/neopixel"
        data = dict(
            r = 0,
            g = 0,
            b = 0,
            w = 0,
            brightness = 0,)
        self.arduino_manager.send(path, **data)
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