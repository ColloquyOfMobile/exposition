# from collo.thread_driver import ThreadDriver
from colloquy.neopixel_driver import NeopixelDriver
from colloquy.thread_driver import ThreadDriver
from pathlib import Path
from threading import Event
from collections import deque
from time import time, sleep

# During search the male blinks.
# The blink pattern define 2 things:
# - the male identity: 1 or 2
# - which kind of interation the male is look for (drive state): "O" or "P" or both
# Extracted from TJ's arduino code "logic35_system.ino, line 87."
LIGHT_PATTERNS = {
    "male1": {
        tuple():     (1, 1, 0, 0, 1, 1, 0, 0, 0, 1),
        ("O",):      (1, 1, 0, 0, 0, 0, 0, 1, 1, 1),
        ("P",):      (1, 1, 0, 0, 0, 0, 1, 1, 1, 0),
        ("O", "P"): (1, 1, 0, 0, 0, 1, 0, 1, 0, 1),
    },
    "male2": {
        tuple():     (1, 1, 0, 0, 1, 1, 1, 0, 0, 0),
        ("O",):      (1, 1, 0, 0, 0, 1, 1, 1, 0, 0),
        ("P",):      (1, 1, 0, 0, 1, 0, 0, 0, 1, 1),
        ("O", "P"): (1, 1, 0, 0, 1, 0, 1, 0, 1, 0),
    }
}

class BodyNeopixels(ThreadDriver):

    def __init__(self, owner):
        ThreadDriver.__init__(self, name="body", owner=owner)
        self.ring = NeopixelDriver(owner=self, name="ring")
        self.drive = NeopixelDriver(owner=self, name="drive")
        self.light_patterns = {}
        for k, v in LIGHT_PATTERNS[owner.name].items():
            # The deque with max_len will act as circular list
            self.light_patterns[k] = deque(v, maxlen=len(v))
        self._timestamp = None

    # @property
    # def name(self):
        # return self._owner.name

    @property
    def arduino_manager(self):
        return self._owner.arduino_manager

    @property
    def drives(self):
        return self._owner.drives

    def off(self):
        self.ring.off()
        self.drive.off()

    def __enter__(self):
        light_pattern = self.light_patterns[self.drives.state]

        self._timestamp = time()
        value = light_pattern.popleft()
        light_pattern.append(value)
        self.ring.set(value)

    def _loop(self):
        if (time() - self._timestamp) > 0.5:
            light_pattern = self.light_patterns[self.drives.state]
            value = light_pattern.popleft()
            light_pattern.append(value)
            self.ring.set(value)
            self._timestamp = time()
        # self.sleep_min()

    def stop(self):
        self.ring.off()
        self.drive.off()
        ThreadDriver.stop(self)

    # def stop(self):
        # ThreadDriver.stop(self)
        # except Exception:
            # msg = traceback.format_exc()
            # self.log(msg)
            # self.colloquy.stop_event.set()
            # raise
    # @property
    # def state(self):
        # return self._on_off_state

    # @property
    # def configuration(self):
        # return {
            # "red": self.red,
            # "green": self.green,
            # "blue": self.blue,
            # "white": self.white,
            # "brightness": self.brightness,
        # }

    # def configure(self, red, green, blue, white, brightness):
        # self.red = red
        # self.green = green
        # self.blue = blue
        # self.white = white
        # self.brightness = brightness
        # self._update()

    # def _update(self):
        # if not self._on_off_state:
            # return
        # # path = f"{self._owner.name}/neopixel"
        # data = dict(
            # r = self.red,
            # g = self.green,
            # b = self.blue,
            # w = self.white,
            # brightness = self.brightness)
        # self.arduino_manager.send(self._path, **data)

    # def on(self):
        # self._on_off_state = True
        # self._update()

    # def toggle(self):
        # if self._on_off_state is None:
            # self.on()
            # return

        # if self._on_off_state:
            # self.off()
            # return

        # if not self._on_off_state:
            # self.on()
            # return

    # def set(self, value):
        # if value:
            # self.on()
        # else:
            # self.off()

# # TODO: If time, look into subclassing the NeopixelDriver directly
# class RingPixel(_NeopixelDriver):

    # def __init__(self, owner):
        # _NeopixelDriver.__init__(self, owner, arduino_manager)
        # self._owner = owner
        # self._name = f"{owner.name}/ring"
        # # self.neopixel = NeopixelDriver(owner=self, arduino_manager=owner.arduino_manager)

    # @property
    # def name(self):
        # return self._name

    # def configure(self, red, green, blue, white, brightness):
        # self.neopixel.configure(red, green, blue, white, brightness)

    # def on(self):
        # self.neopixel.on()

    # def off(self):
        # self.neopixel.off()

    # def toggle(self):
        # self.neopixel.toggle()

    # def set(self, value):
        # self.neopixel.set(value)


# class DrivePixel:

    # def __init__(self, owner):
        # self._owner = owner
        # self._name = f"{owner.name}/drive"
        # self.neopixel = NeopixelDriver(owner=self, arduino_manager=owner.arduino_manager)

    # @property
    # def name(self):
        # return self._name

    # def configure(self, red, green, blue, white, brightness):
        # self.neopixel.configure(red, green, blue, white, brightness)

    # def on(self):
        # self.neopixel.on()

    # def off(self):
        # self.neopixel.off()

    # def toggle(self):
        # self.neopixel.toggle()

    # def set(self):
        # self.neopixel.set()