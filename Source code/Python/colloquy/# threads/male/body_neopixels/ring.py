from colloquy.neopixel import Neopixel
from pathlib import Path
from threading import Event

class Ring(Neopixel):

    def __init__(self, owner, name):
        Neopixel.__init__(self, owner=owner, name=name)

    def set_test_default(self):
        self.configure(red=0, green=0, blue=0, white=255, brightness=255)
        self.on()