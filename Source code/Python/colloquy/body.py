from .moving_part import MovingPart
from .speaker import Speaker
from pathlib import Path
from threading import Event
from threading import Timer
import traceback


class Body(MovingPart):

    def __init__(self, owner, **kwargs):
        dxl_manager = kwargs["dynamixel manager"]
        MovingPart.__init__(self, owner, **kwargs)
        self.arduino_manager = kwargs["arduino manager"]
        self.interaction_event = Event()
        self._speaker = Speaker(owner=self, arduino_manager=self.arduino_manager)
        self._microphone = None
        self._near_origin_threashold = 400

    @property
    def speaker(self):
        return self._speaker

    @property
    def search(self):
        return self._search

    @property
    def microphone(self):
        return self._microphone

    @microphone.setter
    def microphone(self, value):
        self._microphone = value

    def near_origin(self):
        min = self.dxl_origin - self._near_origin_threashold
        max = self.dxl_origin + self._near_origin_threashold
        return min < self.position < max

    def open(self):
        MovingPart.open(self)

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