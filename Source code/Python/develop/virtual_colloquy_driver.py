from .virtual_dynamixel_manager import VirtualDynamixelManager
from .virtual_arduino_manager import VirtualArduinoManager
# from .virtual_female_driver import VirtualFemaleDriver
# from .virtual_male_driver import VirtualMaleDriver
# from .virtual_bar_driver import VirtualBarDriver
from time import sleep
from parameters import Parameters
from colloquy_driver import ColloquyDriver


class VirtualColloquyDriver(ColloquyDriver):

    _classes = ColloquyDriver._classes.copy()
    _classes.update({
        "dxl_manager": VirtualDynamixelManager,
        "arduino_manager": VirtualArduinoManager,
        # "virtual_female_driver": VirtualFemaleDriver,
        # "virtual_male_driver": VirtualMaleDriver,
        # "virtual_bar_driver": VirtualBarDriver,
    })
    def __init__(self, params, ):
        ColloquyDriver.__init__(self, params, name="Virtual Colloquy driver")