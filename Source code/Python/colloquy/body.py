from .shared_driver import SharedDriver
from .speaker_driver import SpeakerDriver
from .drives_handler import DrivesHandler
from pathlib import Path
from threading import Event
from threading import Timer
import traceback


class Body(SharedDriver):

    def __init__(self, owner, **kwargs):
        dxl_manager = kwargs["dynamixel manager"]
        SharedDriver.__init__(self, owner, **kwargs)
        # self.colloquy = kwargs["colloquy"]
        self.arduino_manager = kwargs["arduino manager"]
        # elf._speaker_memory = None
        self.interaction_event = Event()
        self.drives = DrivesHandler(owner=self)
        self.speaker = SpeakerDriver(owner=self, arduino_manager=self.arduino_manager)

    # @property
    # def speaker_state(self):
        # return self._speaker_memory

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

    def toggle_neopixel(self):
        self.neopixel.toggle()

    def turn_on_neopixel(self):
        self.neopixel.on()

    def turn_off_neopixel(self):
        self.neopixel.off()