from dynamixel_manager import DynamixelManager
from arduino_manager import ArduinoManager
from female_driver import FemaleDriver
from male_driver import MaleDriver
from bar_driver import BarDriver
from time import sleep
from parameters import Parameters


class ColloquyDriver:

    def __init__(self, params):
        print(f"Initialising Colloquy driver...")
        self.mirrors = []
        self.males = []
        self.bodies = []
        self.elements = []
        self.bar = None

        self._dxl_manager = dxl_manager = None
        self._arduino_manager = arduino_manager =None

        dxl_network = params.get("dynamixel network", {})
        dxl_com = dxl_network.get("communication port")

        if dxl_com is not None:
            print(f"| Initialising DXL manager...")
            self._dxl_manager = dxl_manager = DynamixelManager(**dxl_network)

        arduino_params = params.get("arduino", {})
        arduino_com = arduino_params.get("communication port")
        if arduino_com is not None:
            print(f"| Initialising Arduino manager...")
            self._arduino_manager = arduino_manager = ArduinoManager(**arduino_params)

        self.females = []
        females_params = params.get("females", {})
        females_names = females_params.get("names", [])
        for name in females_names:
            print(f"| Initialising {name} driver...")
            fem_params = dict(params[name])
            fem_params["name"] = name
            fem_params.update( params["females"]["share"])
            fem_params["dynamixel manager"] = dxl_manager
            fem_params["arduino manager"] = arduino_manager


            female_driver = FemaleDriver(**fem_params)
            self.females.append(female_driver)

            setattr(self, name, female_driver)

            if female_driver.mirror is not None:
                self.mirrors.append(female_driver.mirror)

        self.males = []
        males_params = params.get("males", {})
        males_names = males_params.get("names", [])
        for name in males_names:
            print(f"| Initialising {name} driver...")
            male_params = dict(params[name])
            male_params["name"] = name
            male_params.update( params["males"]["share"])
            male_params["dynamixel manager"] = dxl_manager
            male_params["arduino manager"] = arduino_manager
            male_driver = MaleDriver(**male_params)
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

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    @property
    def arduino(self):
        return self._arduino_manager

    def turn_to_origin_position(self, elements):
        for element in elements:
            element.turn_to_origin_position()

    def turn_to_max_position(self, elements):
        for element in elements:
            element.turn_to_max_position()

    def turn_to_min_position(self, elements):
        for element in elements:
            element.turn_to_min_position()

    def turn_on_neopixel(self, elements):
        for element in elements:
            element.turn_on_neopixel()

    def turn_off_neopixel(self, elements):
        for element in elements:
            element.turn_off_neopixel()

    def play_pacman(self, elements):
        path = f"female1/pacman"
        data = ""
        print(f"{path=}")
        response = self.female1.arduino_manager.send(path, data)
        print(response)

    def play_pinkpanther(self,):
        path = f"female1/pinkpanther"
        data = ""
        print(f"{path=}")
        response = self.female1.arduino_manager.send(path, data)
        print(response)

    def is_something_moving(self):
        return any(
            (e.is_moving
            for e
            in self.elements)
        )

    def wait_until_everything_is_still(self):
        while self.is_something_moving():
            sleep(0.1)

    def calibrate(self):
        import code
        colloquy = self
        locals_dict = {
            "female1": self.female1,
            "female2": self.female2,
            "female3": self.female3,
            "mirror1": self.female1.mirror,
            "mirror2": self.female2.mirror,
            "mirror3": self.female3.mirror,
            "male1": self.male1,
            "male2": self.male2,
            }

        code.interact(local=locals_dict, banner=CALIBRATION_BANNER)

    def run(self):
        raise NotImplementedError

    def start(self):
        print("Starting Colloquy...")
        if self._dxl_manager is not None:
            self._dxl_manager.start()
        if self._arduino_manager is not None:
            self._arduino_manager.start()

    def stop(self):
        if self._dxl_manager is not None:
            self._dxl_manager.stop()
        if self._arduino_manager is not None:
            self._arduino_manager.stop()
        print("Colloquy stopped.")

CALIBRATION_BANNER = """#########################################################
This small script is for mecanical calibration.

Normally, the calibration should be done after every motor assembly.

Running this script will return an interactive python console, in which you can run python command directly.
To exit the calibration process:
>>> exit()

The aim is to:
- move the females carefully to point them all at the center of the artwork.
- move the males carefully to point them all outwards and aligned with the bar.
- move the bar carefully to point in direction of female 1. Check the cables.


The useful command are (replace female1 by the interested part):
- colloquy.female1.position: returns the current position as seen by the motor.
- colloquy.female1.move_and_wait(position=2200): Turn the female to desired position.
- colloquy.female1.mirror.position: FEMALE ONLY, returns the current position as seen by the motor.
- colloquy.female1.mirror.move_and_wait(position=1200) : Turn the mirror to desired position.

The attribute "female1" can be replace by "female2", "female3", "male1", "male2", "bar".
The attribute "body" can be replace by "mirror".

Calibration steps:
1. Use the colloquy.female1.position() to check the present female1's position.
2. Use the colloquy.female1.move_and_wait() to align the female1 to the wanted origin (the body will move symmetrically from this origin).
3. Copy the origin and paste the value in colloquy_driver.py, FEMALE1_ORIGIN
4. Repeat for the process the other females, males



Example:
>>> female1.position
2645
>>> female1.move_and_wait(position=2000)
>>> female1.move_and_wait(position=2300)
>>> female1.move_and_wait(position=2200)
... When happy with origin write FEMALE1_ORIGIN=2200, in file colloquy_mecanical_test.py.
>>> exit()

Repeat with other females, males and the bar.

Note: Resolution = 0.087891 unit/°
>>> female1.position
0
>>> female1.move_and_wait(position=2000) # Will turn 175°


WARNING:
Moving threshold = 20 unit !
Example:
>>> female1.position
3000
>>> female1.move_and_wait(position=3010) # ! Won't move because 3010-3000 = 10 < 20
>>> female1.move_and_wait(position=3500) # OK will move.
#########################################################
"""

if __name__ == "__main__":
    COLLOQUY_DRIVER = ColloquyDriver(params=Parameters().as_dict())
    try:
        COLLOQUY_DRIVER.calibrate()
    finally:
        COLLOQUY_DRIVER.close()