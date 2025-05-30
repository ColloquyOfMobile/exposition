from colloquy.dxl import DXL
from colloquy.thread_element import ThreadElement
from time import time, sleep
from threading import Event
from .search import Search

class BarDriver(ThreadElement):

    def __init__(self, owner, **kwargs):
        ThreadElement.__init__(self, name=kwargs["name"], owner=owner)
        self._position_memory = None
        dxl_manager = kwargs["dynamixel manager"]
        dxl_ids = kwargs["dynamixel ids"]
        self.dxl_origin = kwargs["origin"]
        self.motion_range = kwargs["motion range"]
        self.moving_threshold = 20
        self.interaction = None
        self.interaction_event = Event()
        self._nearby_threashold = 500

        self.nearby_positions = []
        self.offset = None
        self.dxl1 = DXL(dxl_manager, dxl_ids[0])
        self.dxl2 = DXL(dxl_manager, dxl_ids[1])

        self._search = Search(owner=self)

    def __enter__(self):
        assert self.dxl_origin is not None, "Calibrate colloquy."
        self.stop_event.clear()

    def __exit__(self, exc_type, exc_value, traceback_obj):
        self.turn_to_origin_position()
        return ThreadElement.__exit__(self, exc_type, exc_value, traceback_obj)

    @property
    def search(self):
        return self._search

    @property
    def position(self):
        return self.dxl1.position

    @property
    def is_moving(self):
        return self.dxl1.is_moving

    @property
    def drive_mode(self):
        return self.dxl1.drive_mode

    @drive_mode.setter
    def drive_mode(self, value):
        self.dxl1.drive_mode = value
        self.dxl2.drive_mode = value

    @property
    def temperature(self):
        temp1 = self.dxl1.temperature
        temp2 = self.dxl2.temperature
        return max((temp1, temp2))

    @property
    def elec_current(self):
        elec_current1 = self.dxl1.elec_current
        elec_current2 = self.dxl2.elec_current
        return elec_current1 + elec_current2

    @property
    def position(self):
        return self.dxl1.position

    @property
    def torque_enabled(self):
        return self.dxl1.torque_enabled

    @torque_enabled.setter
    def torque_enabled(self, value):
        assert self.offset is not None
        self.dxl1.torque_enabled = value
        self.dxl2.torque_enabled = value

    @property
    def is_moving(self):
        return abs(self.dxl1.position - self.dxl1.goal_position) > self.moving_threshold

    @property
    def profile_velocity(self):
        return self.dxl1.profile_velocity

    @profile_velocity.setter
    def profile_velocity(self, value):
        self.dxl1.profile_velocity = value
        self.dxl2.profile_velocity = value

    @property
    def profile_acceleration(self):
        return self.dxl1.profile_acceleration

    @profile_acceleration.setter
    def profile_acceleration(self, value):
        self.dxl1.profile_acceleration = value
        self.dxl2.profile_acceleration = value

    @property
    def goal_position(self):
        return self.dxl1.goal_position

    @goal_position.setter
    def goal_position(self, value):
        assert self.offset is not None
        self.dxl1.goal_position = value
        self.dxl2.goal_position = value + self.offset

    @property
    def operating_mode(self):
        return self.dxl1.operating_mode

    @operating_mode.setter
    def operating_mode(self, value):
        self.dxl1.operating_mode = value
        self.dxl2.operating_mode = value

    def move_and_wait(self, position):
        """Blocking function that sets the body's goal position and wait for it to move."""
        self.goal_position = position
        self.wait_for_servo()

    def wait_for_servo(self):
        """Blocking funtion that waits until the body has reached his goal position."""
        start = time()
        while True:
            if not self.is_moving:
                break
            assert time() - start < 60, "Moving the bar shouldn't take more than 60s!"
            timelap = time() - start

    def open(self):
        for position in sorted(self.colloquy.interactions.from_positions):
            self.nearby_positions.append(position)
        self._init_offset()
        self.torque_enabled = 0

        self.drive_mode = 0

        self.operating_mode = 4
        self.profile_velocity = 16
        self.profile_acceleration = 1


        self.torque_enabled = 1

    def nearby(self, female):
        if not self.search.is_started:
            return
        for interaction in self.colloquy.interactions.from_females[female]:
            min = interaction.position - self._nearby_threashold
            max = interaction.position + self._nearby_threashold
            if min < self.position < max:
                return interaction


    def turn_to_origin_position(self):
        self.goal_position = self.dxl_origin

    def turn_to_max_position(self):
        self.goal_position = self.dxl_origin + self.motion_range

    def turn_to_min_position(self):
        self.goal_position = self.dxl_origin

    def toggle_max_min_position(self):
        if self._position_memory is None:
            self.turn_to_max_position()
            self._position_memory = "max"
            return

        if self._position_memory == "max":
            self.turn_to_min_position()
            self._position_memory = "min"
            return

        if self._position_memory == "min":
            self.turn_to_max_position()
            self._position_memory = "max"
            return

    def toggle_interaction_position(self):
        self.cursor = 0
        position = self.nearby_positions.pop(0)
        self.nearby_positions.append(position)
        self.goal_position = position
        self.interaction = self.colloquy.interactions.from_positions[position]

    # def wait_interaction_end(self):
        # print(f"Waiting interaction end.")
        # interaction = self.interaction
        # busy = interaction.busy

        # while busy():
            # if self.stop_event.is_set():
                # break
            # self._sleep_min()
        # print(f"...Interaction finished.")


    def _init_offset(self):
        """Initialise the offset postision between the two servos."""
        position1 = self.dxl1.position
        position2 = self.dxl2.position
        self.offset = position2 - position1


    def _loop(self):
        return

    def _set_origin(self, origin):
        origin = int(origin[0])
        self.dxl_origin = origin
        self.colloquy.params[self.name]["origin"] = origin
        self.colloquy.save()

    def add_html(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("h3"):
            text(f"{self.name.title()}:")

        with tag("form", method="post"):
            with tag("label", **{"id": f"{self.name}/origin"}):
                text(f"Origin:")
                kwargs = {}
                if self.dxl_origin is not None:
                    kwargs = {"value": self.dxl_origin}

            with tag("input", type="number", id=f"{self.name}/origin", name="origin", **kwargs):
                pass

            with tag("button", name="action", value=f"{self.name}/origin/set"):
                text(f"set.")

            self.colloquy.actions[f"{self.name}/origin/set"] = self._set_origin