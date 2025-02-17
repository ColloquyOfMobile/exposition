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
    }

    def __init__(self, params):
        print(f"Initialising Colloquy driver...")
        self.mirrors = []
        self.males = []
        self.bodies = []
        self.elements = []
        self.bar = None

        self._dxl_manager = dxl_manager = None
        self._arduino_manager = arduino_manager =None

        dxl_network = params["dynamixel network"]
        self._dxl_manager = dxl_manager = self._classes["dxl_manager"](**dxl_network)

        arduino_params = params["arduino"]
        self._arduino_manager = arduino_manager = self._classes["arduino_manager"](**arduino_params)

        self.females = []
        females_params = params["females"]
        females_names = females_params["names"]
        for name in females_names:
            fem_params = dict(params[name])
            fem_params["name"] = name
            fem_params.update( params["females"]["share"])
            fem_params["dynamixel manager"] = dxl_manager
            fem_params["arduino manager"] = arduino_manager
            female_driver = self._classes["female_driver"](**fem_params)
            self.females.append(female_driver)
            setattr(self, name, female_driver)
            self.mirrors.append(female_driver.mirror)

        self.males = []
        males_params = params["males"]
        males_names = males_params["names"]
        for name in males_names:
            male_params = dict(params[name])
            male_params["name"] = name
            male_params.update( params["males"]["share"])
            male_params["dynamixel manager"] = dxl_manager
            male_params["arduino manager"] = arduino_manager
            male_driver = self._classes["male_driver"](**male_params)
            self.males.append(male_driver)
            setattr(self, name, male_driver)

        self.bodies = [
            *self.females,
            *self.males,
            ]

        self.elements = [
            *self.females,
            *self.mirrors,
            *self.males,
        ]

        bar_params = dict(params["bar"])
        bar_params["name"] = "bar"
        bar_params["dynamixel manager"] = dxl_manager
        if bar_params["origin"] is not None:
            self.bar = BarDriver(**bar_params)