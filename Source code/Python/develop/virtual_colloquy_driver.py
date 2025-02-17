from .virtual_dynamixel_manager import VirtualDynamixelManager
from .virtual_arduino_manager import VirtualArduinoManager
from .virtual_female_driver import VirtualFemaleDriver
from .virtual_male_driver import VirtualMaleDriver
from .virtual_bar_driver import VirtualBarDriver
from time import sleep
from parameters import Parameters
from colloquy_driver import ColloquyDriver


class VirtualColloquyDriver(ColloquyDriver):

    _classes = {
        "dxl_manager": VirtualDynamixelManager,
        "arduino_manager": VirtualArduinoManager,
        "female_driver": VirtualFemaleDriver,
        "male_driver": VirtualMaleDriver,
        "bar_driver": VirtualBarDriver,
    }