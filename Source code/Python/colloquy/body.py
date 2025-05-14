from .shared_driver import SharedDriver
from .speaker_driver import SpeakerDriver
from pathlib import Path
from threading import Event
from threading import Timer
import traceback


class Body(SharedDriver):

    def __init__(self, owner, **kwargs):
        dxl_manager = kwargs["dynamixel manager"]
        SharedDriver.__init__(self, owner, **kwargs)
        self.arduino_manager = kwargs["arduino manager"]
        self.interaction_event = Event()
        self.speaker = SpeakerDriver(owner=self, arduino_manager=self.arduino_manager)
    
    @property
    def search(self):
        return self._search

    def open(self):
        SharedDriver.open(self)

    def turn_to_left_position(self):
        self.turn_to_max_position()

    def turn_to_right_position(self):
        self.turn_to_min_position()

    def turn_on_speaker(self):
        self.speaker.on()

    def turn_off_speaker(self):
        self.speaker.off()

    def toggle_speaker(self):
        self.speaker.toggle()

    def _set_origin(self, origin):
        origin = int(origin[0])
        self.dxl_origin = origin
        self.colloquy.params[self.name]["origin"] = origin
        self.colloquy.save()