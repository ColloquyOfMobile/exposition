from colloquy.body import Body
from colloquy.thread_driver import ThreadDriver
from colloquy.neopixel_driver import NeopixelDriver
from .body_neopixels import BodyNeopixels
from time import time, sleep
from threading import Event, Thread
import traceback


class MaleDriver(Body):

    def __init__(self, **kwargs):
        # dxl_manager = kwargs["dynamixel manager"]
        Body.__init__(
            self,
            **kwargs,
            )
        self.body_neopixel = BodyNeopixels(owner=self)
        self.up_ring = NeopixelDriver(owner=self, name="up_ring")

    def open(self):
        Body.open(self)
        self.body_neopixel.off()

    def __enter__(self):
        self.body_neopixel.ring.configure(
            red = 0,
            green = 0,
            blue = 0,
            white = 255,
            brightness = 255,)
        self.stop_event.clear()
        self.body_neopixel.start()

        self.drives.start()
        self.body_neopixel.drive.on()
        self._update_drive_pixel()

    def _loop(self):
        self._update_drive_pixel()

        if not self.is_moving:
            self.toggle_position()
        # self.sleep_min()

        if self.interaction_event.is_set():
            self._interact()

    def _interact(self):
        self.body_neopixel.ring.on()

        iterations = 2
        self.turn_to_origin_position()
        while self.interaction_event.is_set():
            if self.stop_event.is_set():
                break
            # print(f"{self.name} interacting... ({(i+1)/iterations:.0%})")
            self._sleep_min()

        self.interaction_event.clear()

        self.turn_on_speaker()
        sleep(0.5)
        self.turn_off_speaker()
        print(f"{self.name} finished interaction.")

    def _update_drive_pixel(self):
        state, brightness, color= self.drives.value
        # color = self._light_colors[state]
        config = dict(
            brightness = brightness,
            **color,
            )
        self.body_neopixel.drive.configure(**config)