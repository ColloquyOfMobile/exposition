from .dxl_u2d2 import DXLU2D2
from .arduino_manager import ArduinoManager
from .female import FemaleDriver
from .male import MaleDriver
from .bar import BarDriver
from .logger import Logger
from .thread_element import ThreadElement
from .interactions import Interactions
from time import sleep
from threading import Event, Lock # Thread
from datetime import datetime
from .interaction_counter import InteractionCounter

class Hardware(ThreadElement):

    _classes = {
        "dxl_manager": DXLU2D2,
        "arduino_manager": ArduinoManager,
        "female": FemaleDriver,
        "male": MaleDriver,
        "bar": BarDriver,
    }

    def __init__(self, owner, params, name="hardware"):
        ThreadElement.__init__(self, name=name, owner=owner)
        self._lock = Lock()

        self.opened = None
        self._is_connected = False
        self._name = name
        self.mirrors = []
        self.males = []
        self.bodies = []
        self.speakers = []
        self.bar = None
        self._threads = set()
        self.females = []
        self.males = []
        self._arduino_manager = arduino_manager = None
        self._dxl_manager = dxl_manager = None
        self._doc = None
        self.emulate_light_sensors = True
        self.interaction_counter = InteractionCounter()

        dxl_manager_params = params["dynamixel network"]
        dxl_manager_params["name"] = "dxl"
        self._dxl_manager = dxl_manager = self._classes["dxl_manager"](owner=self, **dxl_manager_params)

        arduino_params = params["arduino"]
        arduino_params["name"] = "arduino_driver"
        self._arduino_manager = arduino_manager = self._classes["arduino_manager"](owner=self, **arduino_params)

        self._init_females(params)
        self._init_males(params)
        self._init_bar(params)

        self.interactions = Interactions(owner=self)

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

    def __enter__(self):
        self.stop_event.clear()
        self.turn_to_origin_position(elements=self.moving_elements)
        self.wait_until_everything_is_still()

        for body in self.bodies:
            body.start()

        self.bar.start()

    def __exit__(self, exc_type, exc_value, traceback_obj):
        print(f"Exiting {self=}")
        result = ThreadElement.__exit__(self, exc_type, exc_value, traceback_obj)
        self.turn_to_origin_position(
            elements=self.moving_elements
        )
        self.wait_until_everything_is_still()
        self._dxl_manager.stop()
        return result

    @property
    def params(self):
        return self.owner.params

    @property
    def near_origin_threashold(self):
        return self.owner.near_origin_threashold


    @property
    def lock(self):
        return self._lock

    @property
    def hardware(self):
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
    def is_connected(self):
        return self._is_connected

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
        # print(f"{self.thread_count=}")
        # for t in self.iter_thread_pool():
            # print(f"  - {t.name}")
        # for e in self.moving_elements:
            # if e.is_moving:
                # print(f"{e=} is moving...")
                # dxl_id = e.dxl.dxl_id
                # dxl_emulator = self._dxl_manager.dxls[dxl_id]
                # print(f"{dxl_id=} {dxl_emulator.is_started}...")
        return any(
            (e.is_moving
            for e
            in self.moving_elements)
        )

    def wait_until_everything_is_still(self):
        print(f"Waiting until everything is still...")
        while self.is_something_moving():
            sleep(0.5)

    def connect(self, **kwargs):
        if self._is_connected:
            return
        self._dxl_manager.open()
        self._arduino_manager.open()

        for body in self.bodies:
            body.open()

        self.bar.open()
        # self.owner.opened = self
        # self._actions = {}
        self._is_connected = True
        self.turn_to_origin_position(elements=self.moving_elements)
        self.wait_until_everything_is_still()


    def close(self, **kwargs):
        print(f"{self.interaction_counter.frequency=}")
        self._actions = None
        if not self._is_connected:
            return

        # if self.thread is not None:
        self.stop()

        for element in self.moving_elements:
            element.dxl.torque_enabled = False

        self.bar.turn_to_origin_position()
        self._dxl_manager.close()
        self._arduino_manager.close()
        self._is_connected = False

    def save(self):
        self.params.save()

    def write_html(self):
        doc, tag, text = self.html_doc.tagtext()

        self.actions.clear()

        if self.opened:
            self.opened.write_html()
            return

    def _init_bar(self, params):
        bar_params = dict(params["bar"])
        bar_params["hardware"] = self
        bar_params["name"] = "bar"
        bar_params["dynamixel manager"] = self._dxl_manager
        bar_params["hardware"] = self
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
            fem_params["hardware"] = self
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
            male_params["hardware"] = self
            male = self._classes["male"](owner=self, **male_params)
            self.males.append(male)
            setattr(self, name, male)

    # def _write_html_open(self):
        # doc, tag, text = self.html_doc.tagtext()
        # # self._write_html_action(value="hardware/open", label=self.name, func=self.open)

    def _loop(self):
        pass