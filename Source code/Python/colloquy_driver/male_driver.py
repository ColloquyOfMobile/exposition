from .male_female_driver import FemaleMaleDriver
from time import time, sleep
from threading import Event

class MaleDriver(FemaleMaleDriver):

    def __init__(self, **kwargs):
        dxl_manager = kwargs["dynamixel manager"]
        FemaleMaleDriver.__init__(
            self,
            **kwargs,
            )
        self.speaker = None
        self.neopixel = None
        self._blink_profile = [12.75, 21.45, 22.05, 22.25, 22.55, 22.70, 22.95, 23.05, 25.55]

    def run(self, **kwargs):
        self.stop_event = Event()
        blink_profile = list(self._blink_profile)

        neopixel_start = time()
        duration = blink_profile.pop(0)

        self.turn_on_neopixel()

        while not self.stop_event.is_set():
            if time() - neopixel_start > duration:
                self.toggle_neopixel()
                neopixel_start = time()