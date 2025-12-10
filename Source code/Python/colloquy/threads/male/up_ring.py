from colloquy.neopixel import Neopixel
from pathlib import Path
from threading import Event

class UpRing(Neopixel):

    def __init__(self, owner, name):
        Neopixel.__init__(self, owner=owner, name=name)

        # raise NotImplementedError(f"{kwargs=}")

    # def rgb_to_hex(self, red, green, blue):
        # for value in (red, green, blue):
            # assert 0 <= value <= 255
        # return '#{:02X}{:02X}{:02X}'.format(red, green, blue)

    # def hex_to_rgb(self, hex_value):
        # hex_value = hex_value.lstrip('#')  # Retire le #
        # if len(hex_value) != 6:
            # raise ValueError("La valeur hexadécimale doit contenir exactement 6 caractères.")
        # r = int(hex_value[0:2], 16)
        # g = int(hex_value[2:4], 16)
        # b = int(hex_value[4:6], 16)
        # return (r, g, b)

    def set_test_default(self):
        self.configure(red=0, green=0, blue=0, white=255, brightness=255)
        self.on()