from .thread_driver import ThreadDriver
from pathlib import Path
from threading import Event

class SpeakerDriver(ThreadDriver):

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

        path = f"{self._owner.name}/speaker"
        self.arduino_manager.send(path, data="on")


    def off(self):
        path = f"{self._owner.name}/speaker"
        self.arduino_manager.send(path, data="off")

    def toggle(self):
        if self._on_off_state is None:
            self.turn_on_speaker()
            self._on_off_state = True
            return

        if self._on_off_state:
            self.turn_off_speaker()
            self._on_off_state = False
            return

        if not self._on_off_state:
            self.turn_on_speaker()
            self._on_off_state = True
            return