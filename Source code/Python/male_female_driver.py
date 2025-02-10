from shared_driver import SharedDriver
from pathlib import Path

class FemaleMaleDriver(SharedDriver):

    def __init__(self, **kwargs):
        dxl_manager = kwargs["dynamixel manager"]
        SharedDriver.__init__(self, **kwargs)
        self.arduino_manager = kwargs["arduino manager"]
        self._neopixel_memory = None
        self._speaker_memory = None

    def turn_to_left_position(self):
        self.turn_to_max_position()

    def turn_to_right_position(self):
        self.turn_to_min_position()

    def turn_on_neopixel(self):
        path = f"{self.name}/neopixel"
        data = "on" # Turns the Neopixels off.
        self.arduino_manager.send(path, data)
        # raise NotImplementedError

    def turn_off_neopixel(self):
        path = f"{self.name}/neopixel"
        data = "off" # Turns the Neopixels off.
        self.arduino_manager.send(path, data)

    def turn_on_speaker(self):
        path = f"{self.name}/speaker"
        data = "on" # Turns the Neopixels off.
        self.arduino_manager.send(path, data)
        # raise NotImplementedError

    def turn_off_speaker(self):
        path = f"{self.name}/speaker"
        data = "off" # Turns the Neopixels off.
        self.arduino_manager.send(path, data)

    def toggle_neopixel(self):
        if self._neopixel_memory is None:
            self.turn_on_neopixel()
            self._neopixel_memory = True
            return

        if self._neopixel_memory:
            self.turn_off_neopixel()
            self._neopixel_memory = False
            return

        if not self._neopixel_memory:
            self.turn_on_neopixel()
            self._neopixel_memory = True
            return

    def play_pacman(self,):
        path = f"{self.name}/pacman"
        data = ""
        response = self.arduino_manager.send(path, data)
        print(response)

    def toggle_speaker(self):
        print(f"{self._speaker_memory=}")
        if self._speaker_memory is None:
            self.turn_on_speaker()
            self._speaker_memory = True
            return

        if self._speaker_memory:
            self.turn_off_neopixel()
            self._speaker_memory = False
            return

        if not self._speaker_memory:
            self.turn_on_speaker()
            self._speaker_memory = True
            return