from .dxl_driver import DXLDriver
from .thread_driver import ThreadDriver
from threading import Event


class SharedDriver(ThreadDriver):

    classes = {
        "dxl_driver": DXLDriver
    }

    def __init__(self, owner, **kwargs):
        ThreadDriver.__init__(self, name=kwargs["name"], owner=owner)
        # self._owner = owner
        dxl_manager = kwargs["dynamixel manager"]
        dxl_id = kwargs["dynamixel id"]
        self.dxl_origin = kwargs["origin"]
        self.motion_range = kwargs["motion range"]
        # self.stop_event = Event()
        self.dxl = self.classes["dxl_driver"](dxl_manager, dxl_id)

        self._position_memory = None

    @property
    def position(self):
        return self.dxl.position

    @property
    def is_moving(self):
        return self.dxl.is_moving

    def turn_to_origin_position(self):
        self.dxl.goal_position = self.dxl_origin

    def turn_to_max_position(self):
        self.dxl.goal_position = self.dxl_origin + self.motion_range/2
        self._position_memory = "max"

    def turn_to_min_position(self):
        self.dxl.goal_position = self.dxl_origin - self.motion_range/2
        self._position_memory = "min"

    def move_and_wait(self, position):
        """Blocking function that sets the body's goal position and wait for it to move."""
        self.dxl.move_and_wait(position)

    def toggle_position(self):
        if self._position_memory is None:
            self.turn_to_max_position()
            return

        if self._position_memory == "max":
            self.turn_to_min_position()
            return

        if self._position_memory == "min":
            self.turn_to_max_position()
            return

    def close(self):
        raise NotImplementedError

    def open(self):
        self.dxl.open()

    def add_html(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("h3"):
            text(f"{self.name.title()}:")

        if self.colloquy.is_open:
                if not self._is_started:
                    self._add_html_start()
                else:
                    self._add_html_stop()

        self._add_html_params()

    def _add_html_params(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("label", **{"for": f"{self.name}/origin"}):
                text(f"Origin:")
                kwargs = {}
                if self.dxl_origin is not None:
                    kwargs = {"value": self.dxl_origin}

            with tag("input", type="number", id=f"{self.name}/origin", name="origin", **kwargs):
                pass

            with tag("button", name="action", value=f"{self.name}/origin/set"):
                text(f"set.")

            self.colloquy.actions[f"{self.name}/origin/set"] = self._set_origin

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value=f"{self.name}/start"):
                text(f"Start.")
            self.colloquy.actions[f"{self.name}/start"] = self.start

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value=f"{self.name}/stop"):
                text(f"Stop.")
            self.colloquy.actions[f"{self.name}/stop"] = self.stop