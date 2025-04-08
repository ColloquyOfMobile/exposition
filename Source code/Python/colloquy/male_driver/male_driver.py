from colloquy.body import Body
from colloquy.thread_driver import ThreadDriver
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

    def open(self):
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
        self.sleep_min()

        if self.interaction_event.is_set():
            self.body_neopixel.stop()
            self._interact()
            self.body_neopixel.start()

    # def stop(self):
        # self.body_neopixel.ring.off()
        # self._blink_thread.stop()
        # Body.stop(self)

    # def _blink(self):
        # try:
            # light_pattern = self.light_patterns[self.drives.state]

            # neopixel_start = time()
            # value = light_pattern.popleft()
            # light_pattern.append(value)
            # self.body_neopixel.ring.set(value)

            # while not self.stop_event.is_set():
                # if (time() - neopixel_start) > 0.5:
                    # value = light_pattern.popleft()
                    # light_pattern.append(value)
                    # self.body_neopixel.ring.set(value)
                    # neopixel_start = time()

                # if self.interaction_event.is_set():
                    # break
                # self.sleep_min()
        # except Exception:
            # msg = traceback.format_exc()
            # self.log(msg)
            # self.colloquy.stop_event.set()
            # raise

    def _interact(self):
        self.body_neopixel.ring.on()

        iterations = 2
        self.turn_to_origin_position()
        for i in range(iterations):
            if self.stop_event.is_set():
                break
            # print(f"{self.name} interacting... ({(i+1)/iterations:.0%})")
            sleep(1)
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