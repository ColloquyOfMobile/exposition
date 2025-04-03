# from collo.thread_driver import ThreadDriver
from colloquy_driver.neopixel_driver import NeopixelDriver
from colloquy_driver.thread_driver import ThreadDriver
from pathlib import Path
from threading import Event

class BodyNeopixels(ThreadDriver):

    def __init__(self, owner):
        self._owner= owner
        self.ring = NeopixelDriver(owner=self, name="ring")
        self.drive = NeopixelDriver(owner=self, name="drive")

    @property
    def name(self):
        return self._owner.name

    @property
    def arduino_manager(self):
        return self._owner.arduino_manager

    def off(self):
        self.ring.off()
        self.drive.off()
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