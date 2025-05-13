from colloquy_driver.shared_driver import FemaleDriver


class VirtualFemaleDriver(SharedDriver):
    pass

    # def __init__(self, **kwargs):
        # dxl_manager = kwargs["dynamixel manager"]
        # dxl_id = kwargs["dynamixel id"]
        # self.dxl = None
        # self.dxl_origin = kwargs["origin"]
        # self.motion_range = kwargs["motion range"]
        # self.name = kwargs["name"]
        # self.stop_event = None

        # if dxl_manager is not None:
            # self.dxl = DXLDriver(dxl_manager, dxl_id)

        # self._position_memory = None

    # @property
    # def position(self):
        # return self.dxl.position

    # @property
    # def is_moving(self):
        # return self.dxl.is_moving

    # def turn_to_origin_position(self):
        # self.dxl.goal_position = self.dxl_origin

    # def turn_to_max_position(self):
        # self.dxl.goal_position = self.dxl_origin + self.motion_range/2
        # self._position_memory = "max"

    # def turn_to_min_position(self):
        # self.dxl.goal_position = self.dxl_origin - self.motion_range/2
        # self._position_memory = "min"

    # def move_and_wait(self, position):
        # """Blocking function that sets the body's goal position and wait for it to move."""
        # self.dxl.move_and_wait(position)

    # def toggle_position(self):
        # if self._position_memory is None:
            # self.turn_to_max_position()
            # return

        # if self._position_memory == "max":
            # self.turn_to_min_position()
            # return

        # if self._position_memory == "min":
            # self.turn_to_max_position()
            # return

    # def stop(self):
        # raise NotImplementedError