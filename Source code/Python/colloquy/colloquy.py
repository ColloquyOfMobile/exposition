from .dxl_u2d2 import DXLU2D2
from .arduino_manager import ArduinoManager
from .female import FemaleDriver
from .male import MaleDriver
from .bar import BarDriver
from .logger import Logger
from .thread_element import ThreadElement
from .interactions import Interactions
from .tests import Tests
from parameters import Parameters
from time import sleep
from threading import Event, Lock # Thread

class Colloquy(ThreadElement):

    _classes = {
        "dxl_manager": DXLU2D2,
        "arduino_manager": ArduinoManager,
        "female": FemaleDriver,
        "male": MaleDriver,
        "bar": BarDriver,
    }

    def __init__(self, owner, name="colloquy"):
        ThreadElement.__init__(self, name=name, owner=owner)
        self._lock = Lock()
        self._params = Parameters(owner=self)
        params = self.params.as_dict()

        self.opened = None
        self._is_open = False
        self._name = name
        self.mirrors = []
        self.males = []
        self.bodies = []
        self.bar = None
        self._threads = set()
        self.females = []
        self.males = []
        self._arduino_manager = arduino_manager = None
        self._dxl_manager = dxl_manager = None
        self._doc = None

        dxl_manager_params = params["dynamixel network"]
        dxl_manager_params["name"] = "dxl"
        self._dxl_manager = dxl_manager = self._classes["dxl_manager"](owner=self, **dxl_manager_params)

        arduino_params = params["arduino"]
        arduino_params["name"] = "arduino_driver"
        self._arduino_manager = arduino_manager = self._classes["arduino_manager"](owner=self, **arduino_params)

        self._init_females(params)
        self._init_males(params)

        self.interactions = None
        self._tests = Tests(owner=self)
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
        if not self.params.is_calibrated:
            self.params.open()

    def __enter__(self):
        self.stop_event.clear()
        self.turn_to_origin_position(elements=self.moving_elements)
        self.wait_until_everything_is_still()

        for body in self.bodies:
            body.start()

        self.bar.start()

    def __exit__(self, exc_type, exc_value, traceback_obj):
        result = ThreadElement.__exit__(self, exc_type, exc_value, traceback_obj)
        self.turn_to_origin_position(
            elements=self.moving_elements
        )
        self.wait_until_everything_is_still()
        self._dxl_manager.stop()
        return result

    @property
    def lock(self):
        return self._lock

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
    def dxl_manager(self):
        return self._dxl_manager

    @property
    def interaction(self):
        return self.bar.interaction

    @interaction.setter
    def interaction(self, value):
        self.bar.interaction = value

    @property
    def is_open(self):
        return self._is_open

    def turn_to_interaction_position(self):
        position = self.interaction.position # + self.bar.dxl_origin
        self.bar.goal_position = position

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

    def open(self, **kwargs):
        assert not self.opened # params should be closed
        if self._is_open:
            return
        self.interactions = Interactions(owner=self)
        self._dxl_manager.open()
        self._arduino_manager.open()

        for body in self.bodies:
            body.open()

        self.bar.open()
        self.owner.opened = self
        # self._actions = {}
        self._is_open = True

    def close(self, **kwargs):
        self._actions = None
        if not self._is_open:
            return

        if self.thread is not None:
            self.stop()

        self.bar.turn_to_origin_position()
        self._dxl_manager.close()
        self._arduino_manager.close()
        self._is_open = False

        print("Colloquy closed.")

    def save(self):
        self.params.save()

    def write_html(self):
        doc, tag, text = self.html_doc.tagtext()

        self.actions.clear()

        if self.opened:
            self.opened.write_html()
            return
        self._add_html_thread_count()
        if not self.is_open:
            # self.params.write_html()
            self._write_html_open()
            return

        doc.stag("hr")
        if not self.is_started:
            self._add_html_start()
        else:
            self._add_html_stop()
        doc.stag("hr")

        self._tests.add_html()
        # doc.stag("hr")

        # with tag("h2"):
            # text("Elements")
        # for element in sorted([*self.elements, *self.mirrors]):
            # element.add_html()

    def _add_html_thread_count(self):
        doc, tag, text = self.html_doc.tagtext()
        if self.thread_count:
            with tag("details",):
                with tag("summary",):
                    text(
                        f"threads: {self.thread_count}"
                        )
                for e in self.iter_thread_pool():
                    with tag("summary",):
                        text(
                            f"{e.name}"
                            )

    def _init_bar(self, params):
        bar_params = dict(params["bar"])
        bar_params["colloquy"] = self
        bar_params["name"] = "bar"
        bar_params["dynamixel manager"] = self._dxl_manager
        bar_params["colloquy"] = self
        self.bar = self._classes["bar"](owner=self, **bar_params)


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
            female = self._classes["female"](owner=self, **fem_params)
            self.females.append(female)
            setattr(self, name, female)
            self.mirrors.append(female.mirror)

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
            male = self._classes["male"](owner=self, **male_params)
            self.males.append(male)
            setattr(self, name, male)

    def _write_html_open(self):
        doc, tag, text = self.html_doc.tagtext()
        self.params.write_html()
        self._write_html_action(value="colloquy/open", label=self.name, func=self.open)

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value="colloquy/start"):
                text(f"Start.")
                self.colloquy.actions["colloquy/start"] = self.start
            with tag("button", name="action", value="colloquy/close"):
                text(f"close.")
                self.actions["colloquy/close"] = self.close

        # self._add_html_interaction()

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value="colloquy/stop"):
                text(f"Stop.")
        self.actions["colloquy/stop"] = self.stop

    def _loop(self):
        pass