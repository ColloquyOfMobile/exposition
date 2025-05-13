from .virtual_dynamixel_manager import VirtualDynamixelManager
from .virtual_arduino_manager import VirtualArduinoManager
from time import sleep
from parameters import Parameters
from colloquy import Colloquy


class VirtualColloquy(Colloquy):

    _classes = Colloquy._classes.copy()
    _classes.update({
        "dxl_manager": VirtualDynamixelManager,
        "arduino_manager": VirtualArduinoManager,
    })
    def __init__(self, owner, ):
        Colloquy.__init__(self, owner)