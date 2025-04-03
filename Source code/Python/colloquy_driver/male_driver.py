from .body import Body
from .thread_driver import ThreadDriver
from .neopixel_driver import NeopixelDriver
from time import time, sleep
from threading import Event, Thread
from collections import deque
import traceback

# During search the male blinks.
# The blink pattern define 2 things:
# - the male identity: 1 or 2
# - which kind of interation the male is look for (drive state): "O" or "P" or both
# Extracted from TJ's arduino code "logic35_system.ino, line 87."
LIGHT_PATTERNS = {
    "male1": {
        None:     (1, 1, 0, 0, 1, 1, 0, 0, 0, 1),
        "O":      (1, 1, 0, 0, 0, 0, 0, 1, 1, 1),
        "P":      (1, 1, 0, 0, 0, 0, 1, 1, 1, 0),
        "O or P": (1, 1, 0, 0, 0, 1, 0, 1, 0, 1),
    },
    "male2": {
        None:     (1, 1, 0, 0, 1, 1, 1, 0, 0, 0),
        "O":      (1, 1, 0, 0, 0, 1, 1, 1, 0, 0),
        "P":      (1, 1, 0, 0, 1, 0, 0, 0, 1, 1),
        "O or P": (1, 1, 0, 0, 1, 0, 1, 0, 1, 0),
    }
}


class MaleDriver(Body):

    def __init__(self, **kwargs):
        # dxl_manager = kwargs["dynamixel manager"]
        Body.__init__(
            self,
            **kwargs,
            )
        self.ring_pixel = RingPixel(owner=self)
        self.drive_pixel = DrivePixel(owner=self)
        self.light_patterns = {}
        for k, v in LIGHT_PATTERNS[self.name].items():
            # The deque with max_len will act as circular list
            self.light_patterns[k] = deque(v, maxlen=len(v))

        self._blink_thread = None
    
    def open(self):
        self.neopixel.off()

    def _run_setup(self):
        self.ring_pixel.configure(
            red = 0,
            green = 0,
            blue = 0,
            white = 255,
            brightness = 255,)
        self.stop_event.clear()
        self._blink_thread = blink_thread = Thread(target=self._blink, name=f"{self.name}/blink")
        blink_thread.start()

        self.drives.start()
        self.drive_pixel.on()
        self._update_drive_pixel()

    def _run_loop(self):
        blink_thread = self._blink_thread
        while not self.stop_event.is_set():

            self._update_drive_pixel()

            if not self.is_moving:
                self.toggle_position()
            self.sleep_min()

            if self.interaction_event.is_set():
                blink_thread.join()
                self._interact()
                blink_thread = self._blink_thread = Thread(target=self._blink, name=f"{self.name}/blink")
                blink_thread.start()

    def _run_setdown(self):
        self.ring_pixel.off()
        print(f"Joining thread {self._blink_thread.name}...")
        self._blink_thread.join()

    def _blink(self):
        try:
            light_pattern = self.light_patterns[self.drives.state]

            neopixel_start = time()
            value = light_pattern.popleft()
            light_pattern.append(value)
            self.ring_pixel.set(value)

            while not self.stop_event.is_set():
                if (time() - neopixel_start) > 0.5:
                    value = light_pattern.popleft()
                    light_pattern.append(value)
                    self.ring_pixel.set(value)
                    neopixel_start = time()

                if self.interaction_event.is_set():
                    break
                self.sleep_min()
        except Exception:
            msg = traceback.format_exc()
            self.log(msg)
            self.colloquy.stop_event.set()
            raise

    def _interact(self):
        self.ring_pixel.on()

        iterations = 2
        self.turn_to_origin_position()
        for i in range(iterations):
            if self.stop_event.is_set():
                break
            # print(f"{self.name} interacting... ({(i+1)/iterations:.0%})")
            sleep(1)
            self.drives.o_drive = self.drives.o_drive / 2
            self.drives.p_drive = self.drives.p_drive / 2

        self.drives.satisfy()

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
        self.drive_pixel.configure(**config)

# TODO: If time, look into subclassing the NeopixelDriver directly
class RingPixel:

    def __init__(self, owner):
        self._owner = owner
        self._name = f"{owner.name}/ring"
        self.neopixel = NeopixelDriver(owner=self, arduino_manager=owner.arduino_manager)

    @property
    def name(self):
        return self._name

    def configure(self, red, green, blue, white, brightness):
        self.neopixel.configure(red, green, blue, white, brightness)

    def on(self):
        self.neopixel.on()

    def off(self):
        self.neopixel.off()

    def toggle(self):
        self.neopixel.toggle()

    def set(self, value):
        self.neopixel.set(value)


class DrivePixel:

    def __init__(self, owner):
        self._owner = owner
        self._name = f"{owner.name}/drive"
        self.neopixel = NeopixelDriver(owner=self, arduino_manager=owner.arduino_manager)

    @property
    def name(self):
        return self._name

    def configure(self, red, green, blue, white, brightness):
        self.neopixel.configure(red, green, blue, white, brightness)

    def on(self):
        self.neopixel.on()

    def off(self):
        self.neopixel.off()

    def toggle(self):
        self.neopixel.toggle()

    def set(self):
        self.neopixel.set()