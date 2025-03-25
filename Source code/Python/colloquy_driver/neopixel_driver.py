from .thread_driver import ThreadDriver
from pathlib import Path
from threading import Event

class NeopixelDriver(ThreadDriver):

    def __init__(self, owner, arduino_manager):
        self._owner = owner
        self.arduino_manager = arduino_manager
        self._on_off_state = None

    def set(self, neopixel_on_off):
        if neopixel_on_off:
            self.on()
        else:
            self.off()

    def on(self):
        path = f"{self._owner.name}/neopixel"
        data = dict(
            r = 0,
            g = 0,
            b = 0,
            w = 255,
            brightness = 255,)
        self.arduino_manager.send(path, **data)
        self._on_off_state = True

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