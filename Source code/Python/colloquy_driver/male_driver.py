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
        self._blink_profile = [
            #on
            12,
            #off
            21,
            #on
            22,
            #off
            22.5,
            #on
            23.5,
            #off
            24,
            #on
            25,
            #off
            25.5,
            #on
            56.5,
            #off
            59
            ]

    def run(self, **kwargs):
        self.stop_event.clear()
        blink_profile = list(self._blink_profile)

        neopixel_start = time()
        timestamp = blink_profile.pop(0)

        self.turn_on_neopixel()

        while not self.stop_event.is_set():
            if (time() - neopixel_start) > timestamp:
                self.toggle_neopixel()
                if not blink_profile:
                    blink_profile.extend(self._blink_profile)
                    neopixel_start = time()

                timestamp = blink_profile.pop(0)
                # neopixel_start = time()

            if not self.is_moving:
                self.toggle_position()

        self.turn_off_neopixel()