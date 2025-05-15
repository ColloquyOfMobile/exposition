from .thread_driver import ThreadDriver
from pathlib import Path
from threading import Event
from time import sleep

class SpeakerDriver(ThreadDriver):

    def __init__(self, owner, arduino_manager):
        self._owner = owner
        self.arduino_manager = arduino_manager
        self._on_off_state = None

    @property
    def is_on(self):
        return self._on_off_state

    def set(self, neopixel_on_off):
        if neopixel_on_off:
            self.on()
        else:
            self.off()

    def on(self):
        path = f"{self._owner.name}/speaker"
        self.arduino_manager.send(path, data="on")
        self._on_off_state = True


    def off(self):
        path = f"{self._owner.name}/speaker"
        self.arduino_manager.send(path, data="off")
        self._on_off_state = False

    def toggle(self):
        if self._on_off_state is None:
            self.on()
            self._on_off_state = True
            return

        if self._on_off_state:
            self.off()
            self._on_off_state = False
            return

        if not self._on_off_state:
            self.on()
            self._on_off_state = True
            return

    def notify(self):
        self.on()
        sleep(0.5)
        self.off()