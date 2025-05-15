from .dynamixel_manager import DynamixelManager
from .arduino_manager import ArduinoManager
from .female_driver import FemaleDriver
from .male_driver import MaleDriver
from .bar_driver import BarDriver
from .logger import Logger
from .thread_driver import ThreadDriver
from .nearby_interaction import NearbyInteraction
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
        nearby_interactions = [
            NearbyInteraction(owner=self, male=self.male1, female=self.female1, position=0),
            NearbyInteraction(owner=self, male=self.male2, female=self.female3, position=2200),
            NearbyInteraction(owner=self, male=self.male1, female=self.female2, position=4300),
            NearbyInteraction(owner=self, male=self.male2, female=self.female1, position=6200),
            NearbyInteraction(owner=self, male=self.male1, female=self.female3, position=8400),
            NearbyInteraction(owner=self, male=self.male2, female=self.female2, position=10400),
        ]
        self.nearby_interactions = {
            e.position: e for e in nearby_interactions
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

    def __exit__(self, exc_type, exc_value, traceback_obj):
        self.turn_to_origin_position()
        return ThreadDriver.__exit__(self, exc_type, exc_value, traceback_obj)

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
        doc, tag, text = self.html_doc.tagtext()
        self.actions.clear()
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

    def _interact(self, **kwargs):
        male_name = kwargs.pop("male")[0]
        female_name = kwargs.pop("female")[0]
        fem_o_drive = int(kwargs.pop("fem_o_drive")[0])
        fem_p_drive = int(kwargs.pop("fem_p_drive")[0])
        male_o_drive = int(kwargs.pop("male_o_drive")[0])
        male_p_drive = int(kwargs.pop("male_p_drive")[0])
        fem_target_drive = tuple(kwargs.pop("fem_target_drive"))


        for interaction in self.colloquy.nearby_interactions.values():
            if interaction.male.name == male_name:
                if interaction.female.name == female_name:
                    self.colloquy.bar.nearby_interaction = interaction
                    break
        else:
            raise ValueError(f"No interaction found for {female_name=}, {male_name=}")


        interaction.female.drives.o_drive = fem_o_drive
        interaction.female.drives.p_drive = fem_p_drive
        interaction.female.neopixel.on()
        interaction.female.target_drive = interaction.female.drives.state

        interaction.male.drives.o_drive = male_o_drive
        interaction.male.drives.p_drive = male_p_drive
        interaction.male.body_neopixel.drive.on()

        assert interaction.female.drives.is_frustated

        print(f"Move bar to interaction.")
        self.bar.move_and_wait(position = self.bar.nearby_interaction.position+self.bar.dxl_origin)
        # interaction.male.search.start()

        interaction.start()

    def _add_html_open(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value="colloquy/open"):
                text(f"Open.")
        self.colloquy.actions["colloquy/open"] = self.open

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value="colloquy/start"):
                text(f"Start.")
                self.colloquy.actions["colloquy/start"] = self.start
            with tag("button", name="action", value="colloquy/close"):
                text(f"close.")
                self.colloquy.actions["colloquy/close"] = self.close

        self._add_html_interaction()

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value="colloquy/stop"):
                text(f"Stop.")
        self.colloquy.actions["colloquy/stop"] = self.stop

    def _add_html_interaction(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("h2"):
            text("Interact")

        if self.bar.nearby_interaction is None:
            self._add_html_interaction_start()
            return

        else:
            if not self.bar.nearby_interaction.is_started:
                self._add_html_interaction_start()
                return

        self._add_html_interaction_stop()

    def _add_html_interaction_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("div"):
                with tag("label", **{"for": f"{self.name}/interacting_male"}):
                    text(f"Interacting male:")

                with tag("select", name="male", id=f"{self.name}/interacting_male"):
                    with tag("option", value="male1"):
                        text(f"male1")
                    with tag("option", value="male2"):
                        text(f"male2")

            with tag("div"):
                with tag("label", **{"for": f"{self.name}/interacting_female"}):
                    text(f"Interacting female:")

                with tag("select", name="female", id=f"{self.name}/interacting_female"):
                    with tag("option", value="female1"):
                        text(f"female1")
                    with tag("option", value="female2"):
                        text(f"female2")
                    with tag("option", value="female3"):
                        text(f"female3")

            with tag("div"):
                with tag("label", **{"for": f"{self.name}/fem_target_drive"}):
                    text(f"Female target drive (can select one or both):")

                with tag("select", name="fem_target_drive", id=f"{self.name}/fem_target_drive", multiple=True, required=True):
                    with tag("option", value="O", selected=True):
                        text(f"'O'")
                    with tag("option", value="P"):
                        text(f"'P'")

            min_value = 10
            max_value = 255
            with tag("div"):
                with tag("label", **{"for": f"{self.name}/fem_o_drive"}):
                    text(f"Fem O drive:")

                with tag("input", type="number", id=f"{self.name}/fem_o_drive", name="fem_o_drive", value=min_value, min=min_value, max=max_value):
                    pass

            with tag("div"):
                with tag("label", **{"for": f"{self.name}/fem_p_drive"}):
                    text(f"Fem P drive:")

                with tag("input", type="number", id=f"{self.name}/fem_p_drive", name="fem_p_drive", value=min_value, min=min_value, max=max_value):
                    pass

            with tag("div"):
                with tag("label", **{"for": f"{self.name}/male_o_drive"}):
                    text(f"Male O drive:")

                with tag("input", type="number", id=f"{self.name}/male_o_drive", name="male_o_drive", value=min_value, min=min_value, max=max_value):
                    pass

            with tag("div"):
                with tag("label", **{"for": f"{self.name}/male_p_drive"}):
                    text(f"Male P drive:")

                with tag("input", type="number", id=f"{self.name}/male_p_drive", name="male_p_drive", value=min_value, min=min_value, max=max_value):
                    pass

            with tag("button", name="action", value="colloquy/interact"):
                text(f"Start.")

            self.colloquy.actions["colloquy/interact"] = self._interact

    def _add_html_interaction_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        male = self.bar.nearby_interaction.male
        female = self.bar.nearby_interaction.female
        with tag("form", method="post"):
            with tag("div"):
                text(f"Interacting between {male.name}-{female.name}!")

            with tag("button", name="action", value="colloquy/interact/stop"):
                text(f"Stop.")

            self.colloquy.actions["colloquy/interact/stop"] = self.bar.nearby_interaction.stop