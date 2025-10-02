from colloquy.neopixel import Neopixel
from pathlib import Path
from threading import Event

class Ring(Neopixel):

    def __init__(self, owner, name):
        Neopixel.__init__(self, owner=owner, name=name)