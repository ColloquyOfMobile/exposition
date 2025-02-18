from .dxl_driver import DXLDriver
from time import time, sleep
from threading import Event

class BarDriver:

    def __init__(self, **kwargs):
        self._position_memory = None
        dxl_manager = kwargs["dynamixel manager"]
        dxl_ids = kwargs["dynamixel ids"]
        self.dxl = None
        assert kwargs["origin"] is not None, "Calibrate colloquy."
        self.dxl_origin = kwargs["origin"]
        self.motion_range = kwargs["motion range"]
        self.name = kwargs["name"]
        self.moving_threshold = 20
        self.stop_event = Event()

        if dxl_manager is not None:
            self.offset = None
            print(f"| Initialising DXL driver for ID={dxl_ids[0]}...")
            self.dxl1 = DXLDriver(dxl_manager, dxl_ids[0])
            print(f"| Initialising DXL driver for ID={dxl_ids[1]}...")
            self.dxl2 = DXLDriver(dxl_manager, dxl_ids[1])
            self._init_offset()
            self._init()

    def _init_offset(self):
        """Initialise the offset postision between the two servos."""
        position1 = self.dxl1.position
        position2 = self.dxl2.position
        self.offset = position2 - position1

    def _init(self):
        """Initialise the body's position."""
        self.torque_enabled = 0
        # Set velocity base profile.
        self.drive_mode = 0
        # Set expanded position operating mode.
        self.operating_mode = 4

        # set velocity and acceleration profile.
        self.profile_velocity = 16
        self.profile_acceleration = 1

        # Enable torque.
        self.torque_enabled = 1

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
        # raise NotImplementedError
        # self.dxl_body.torque_enabled = 1
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

    def turn_to_origin_position(self):
        self.goal_position = self.dxl_origin

    def turn_to_max_position(self):
        self.goal_position = self.dxl_origin + self.motion_range

    def turn_to_min_position(self):
        self.goal_position = self.dxl_origin

    def toggle_position(self):
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

    def run(self, **kwargs):
        self.stop_event.clear()
        while not self.stop_event.is_set():
            if not self.is_moving:
                self.toggle_position()