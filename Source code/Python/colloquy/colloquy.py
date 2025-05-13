from .dynamixel_manager import DynamixelManager
from .arduino_manager import ArduinoManager
from .female_driver import FemaleDriver
from .male_driver import MaleDriver
from .bar_driver import BarDriver
from .logger import Logger
from .thread_driver import ThreadDriver
from time import sleep
from parameters import Parameters
from threading import Event # Thread

class Colloquy(ThreadDriver):

    _classes = {
        "dxl_manager": DynamixelManager,
        "arduino_manager": ArduinoManager,
        "female_driver": FemaleDriver,
        "male_driver": MaleDriver,
        "bar_driver": BarDriver,
    }

    def __init__(self, owner, name="colloquy"):
        ThreadDriver.__init__(self, name=name, owner=owner)

        self._params =  Parameters(owner=self)# .as_dict()
        params = self._params.as_dict()

        self._is_open = False
        self._name = name
        self.mirrors = []
        self.males = []
        self.bodies = []
        self.actions = {}
        self.bar = None
        self._threads = set()
        self.females = []
        self.males = []
        self._arduino_manager = arduino_manager = None
        self._dxl_manager = dxl_manager = None
        self._doc = None

        dxl_manager_params = params["dynamixel network"]
        dxl_manager_params["name"] = "dxl_driver"
        self._dxl_manager = dxl_manager = self._classes["dxl_manager"](owner=self, **dxl_manager_params)

        arduino_params = params["arduino"]
        arduino_params["name"] = "arduino_driver"
        self._arduino_manager = arduino_manager = self._classes["arduino_manager"](owner=self, **arduino_params)

        self._init_females(params)
        self._init_males(params)

        # Defined at for each bar position, which female and male interacts
        self.nearby_interactions = {
            0: NearbyInteractions(self.male1, self.female1),
            2200: NearbyInteractions(self.male2, self.female3),
            4300: NearbyInteractions(self.male1, self.female2),
            6200: NearbyInteractions(self.male2, self.female1),
            8400: NearbyInteractions(self.male1, self.female3),
            10400: NearbyInteractions(self.male2, self.female2),
        }

        self._init_bar(params)

        self.bodies = [
            *self.females,
            *self.males,
            ]

        self.moving_elements = [
            *self.females,
            *self.mirrors,
            *self.males,
            self.bar
        ]

    @property
    def params(self):
        return self._params

    @property
    def colloquy(self):
        return self

    @property
    def arduino(self):
        return self._arduino_manager

    @property
    def nearby_interaction(self):
        return self.bar.nearby_interaction

    @property
    def is_open(self):
        return self._is_open

    def _init_bar(self, params):
        bar_params = dict(params["bar"])
        bar_params["colloquy"] = self
        bar_params["name"] = "bar"
        bar_params["dynamixel manager"] = self._dxl_manager
        bar_params["colloquy"] = self
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
            in self.moving_elements)
        )

    def wait_until_everything_is_still(self):
        print(f"Waiting until everything is stopped...")
        while self.is_something_moving():
            sleep(0.1)

    def __enter__(self):
        self.stop_event.clear()
        for element in self.moving_elements:
            element.turn_to_origin_position()
        self.wait_until_everything_is_still()

        for body in self.bodies:
            body.start()

        self.bar.start()

    def _loop(self):
        pass

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

        self.bar.turn_to_origin_position()
        self._dxl_manager.close()
        self._arduino_manager.close()

        print("Colloquy closed.")

    def save(self):
        self.params.save()

    def add_html(self):
        self.actions.clear()
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            if not self._is_open:
                self._add_html_open()
            else:
                if not self._is_started:
                    self._add_html_start()
                else:
                    self._add_html_stop()

        with tag("h2"):
            text("Elements")
        for element in sorted([*self.elements, *self.mirrors]):
            element.add_html()

    def _add_html_open(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("button", name="action", value="colloquy/open"):
            text(f"Open.")
        self.colloquy.actions["colloquy/open"] = self.open

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("button", name="action", value="colloquy/start"):
            text(f"Start.")
        self.colloquy.actions["colloquy/start"] = self.start

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("button", name="action", value="colloquy/stop"):
            text(f"Stop.")
        self.colloquy.actions["colloquy/stop"] = self.stop



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