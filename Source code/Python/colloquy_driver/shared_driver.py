from .dxl_driver import DXLDriver


class SharedDriver:

    def __init__(self, **kwargs):
        dxl_manager = kwargs["dynamixel manager"]
        dxl_id = kwargs["dynamixel id"]
        self.dxl = None
        self.dxl_origin = kwargs["origin"]
        self.motion_range = kwargs["motion range"]
        self.name = kwargs["name"]
        self.stop_event = None

        if dxl_manager is not None:
            print(f"| Initialising DXL driver for ID={dxl_id}...")
            self.dxl = DXLDriver(dxl_manager, dxl_id)

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

    def turn_to_min_position(self):
        self.dxl.goal_position = self.dxl_origin - self.motion_range/2

    def move_and_wait(self, position):
        """Blocking function that sets the body's goal position and wait for it to move."""
        self.dxl.move_and_wait(position)

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

    def stop(self):
        raise NotImplementedError