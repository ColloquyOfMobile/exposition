from .dynamixel_manager import DynamixelManager
from .arduino_manager import ArduinoManager
from .female_driver import FemaleDriver
from .male_driver import MaleDriver
from .bar_driver import BarDriver
from .logger import Logger
from .thread_driver import ThreadDriver
from time import sleep
from parameters import Parameters
from threading import Thread, Event

class ColloquyDriver(ThreadDriver):

    _classes = {
        "dxl_manager": DynamixelManager,
        "arduino_manager": ArduinoManager,
        "female_driver": FemaleDriver,
        "male_driver": MaleDriver,
        "bar_driver": BarDriver,
    }

    def __init__(self, params, name="Colloquy driver"):
        print(f"Initialising {name}...")
        self._is_open = False
        self._name = name
        self.mirrors = []
        self.males = []
        self.bodies = []
        self.elements = []
        self.bar = None
        self._stop_event = Event()
        self._threads = set()
        self.females = []
        self.males = []
        self._arduino_manager = arduino_manager = None
        self._dxl_manager = dxl_manager = None


        dxl_manager_params = params["dynamixel network"]
        dxl_manager_params["name"] = "dxl_driver"
        self._dxl_manager = dxl_manager = self._classes["dxl_manager"](**dxl_manager_params)

        arduino_params = params["arduino"]
        arduino_params["name"] = "arduino_driver"
        self._arduino_manager = arduino_manager = self._classes["arduino_manager"](**arduino_params)

        self._init_females(params)
        self._init_males(params)

        # Defined at for each bar position, which female and male interacts
        self.nearby_interactions = {
            0: NearbyInteractions(self.male2, self.female1),
            1600: NearbyInteractions(self.male1, self.female3),
            3900: NearbyInteractions(self.male2, self.female2),
            6500: NearbyInteractions(self.male1, self.female1),
            7900: NearbyInteractions(self.male2, self.female3),
            10200: NearbyInteractions(self.male1, self.female2),
        }

        self._init_bar(params)

        self.bodies = [
            *self.females,
            *self.males,
            ]


        self.elements = [
            *self.females,
            *self.mirrors,
            *self.males,
            self.bar
        ]

    @property
    def stop_event(self):
        return self._stop_event

    @property
    def arduino(self):
        return self._arduino_manager

    @property
    def nearby_interaction(self):
        return self.bar.nearby_interaction

    def _init_bar(self, params):
        bar_params = dict(params["bar"])
        bar_params["colloquy"] = self
        bar_params["name"] = "bar"
        bar_params["dynamixel manager"] = self._dxl_manager
        bar_params["colloquy"] = self
        if bar_params["origin"] is not None:
            self.bar = self._classes["bar_driver"](owner=self, **bar_params)

    def _init_females(self, params, ):
        females_params = params["females"]
        females_names = females_params["names"]
        for name in females_names:
            fem_params = dict(params[name])
            fem_params["name"] = name
            fem_params.update( params["females"]["share"])
            fem_params["dynamixel manager"] = self._dxl_manager
            fem_params["arduino manager"] = self._arduino_manager
            fem_params["colloquy"] = self
            female_driver = self._classes["female_driver"](owner=self, **fem_params)
            self.females.append(female_driver)
            setattr(self, name, female_driver)
            self.mirrors.append(female_driver.mirror)

    def _init_males(self, params, ):
        males_params = params["males"]
        males_names = males_params["names"]
        for name in males_names:
            male_params = dict(params[name])
            male_params["name"] = name
            male_params.update( params["males"]["share"])
            male_params["dynamixel manager"] = self._dxl_manager
            male_params["arduino manager"] = self._arduino_manager
            male_params["colloquy"] = self
            male_driver = self._classes["male_driver"](owner=self, **male_params)
            self.males.append(male_driver)
            setattr(self, name, male_driver)

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

    def is_something_moving(self):
        return any(
            (e.is_moving
            for e
            in self.elements)
        )

    def wait_until_everything_is_still(self):
        print(f"Waiting until everything is stopped...")
        while self.is_something_moving():
            sleep(0.1)

    # def calibrate(self):
        # import code
        # colloquy = self
        # locals_dict = {
            # "female1": self.female1,
            # "female2": self.female2,
            # "female3": self.female3,
            # "mirror1": self.female1.mirror,
            # "mirror2": self.female2.mirror,
            # "mirror3": self.female3.mirror,
            # "male1": self.male1,
            # "male2": self.male2,
            # }

        # code.interact(local=locals_dict, banner=CALIBRATION_BANNER)

    def run(self):
        print(f"Running {self._name}...")
        self.stop_event.clear()
        for element in self.elements:
            element.turn_to_origin_position()
        self.wait_until_everything_is_still()

        for body in self.bodies:
            thread = Thread(target=body.run, name=body.name)
            self._threads.add(thread)
            thread.start()

        thread = Thread(target=self.bar.run, name="bar")
        self._threads.add(thread)
        thread.start()

        while not self.stop_event.is_set():
            self.sleep_min()

        for element in self.elements:
            element.stop_event.set()

        for thread in self._threads:
            thread.join()

    def start(self):
        self.stop_event.clear()
        self.thread = Thread(target=self.run, name=self._name)
        self.thread.start()

    def stop(self):
        if self.stop_event.is_set():
            return
        self.stop_event.set()
        self.thread.join()
        self.thread = None

    def open(self):
        if self._is_open:
            return
        self._dxl_manager.open()
        self._arduino_manager.open()

        for body in self.bodies:
            body.open()

        self.bar.open()
        self._is_open = True

    def close(self):
        if not self._is_open:
            return

        if self.thread is not None:
            self.stop()

        self._dxl_manager.close()
        self._arduino_manager.close()

        print("Colloquy closed.")


class NearbyInteractions:

    def __init__(self, male, female):
        self._male = male
        self._female = female

    def __iter__(self):
        yield self.male
        yield self.female

    @property
    def male(self):
        return self._male

    @property
    def female(self):
        return self._female

    def busy(self):
        return any(
            element.interaction_event.is_set()
            for element
            in self
            )