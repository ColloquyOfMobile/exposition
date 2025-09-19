from .virtual_dynamixel_manager import VirtualDynamixelManager
from .virtual_arduino_manager import VirtualArduinoManager
from .virtual_female import VirtualFemale
from time import sleep
from parameters import Parameters
from colloquy.hardware import Hardware


class VirtualHardware(Hardware):

    _classes = Hardware._classes.copy()
    _classes.update({
        "dxl_manager": VirtualDynamixelManager,
        "arduino_manager": VirtualArduinoManager,
        "female": VirtualFemale,
    })
    # def __init__(self, owner, ):
        # Hardware.__init__(self, owner)