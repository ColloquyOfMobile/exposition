from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS  # Uses Dynamixel SDK library
from time import time, sleep

class DXLDriver:
    def __init__(self, dxl_manager, dynamixel_id):
        # Handle hardware for serial communication.
        self._dxl_manager = dxl_manager
        self._id = dynamixel_id
        self.moving_threshold = 20

    @property
    def dxl_id(self):
        return self._id

    @property
    def drive_mode(self):
        return self._dxl_manager._read_1_byte_at(self._id, 10)

    @drive_mode.setter
    def drive_mode(self, value):
        """
            0x00: velocity based profile.
            0x04: Time base profile.
        """
        return self._dxl_manager._write_1_byte_at(self._id, 10, value)

    @property
    def temperature(self):
        return self._dxl_manager._read_1_byte_at(self._id, 146)

    @property
    def elec_current(self):
        return self._dxl_manager._read_2_bytes_at(self._id, 126)

    @property
    def position(self):
        return self._dxl_manager._read_4_bytes_at(self._id, 132)

    @property
    def torque_enabled(self):
        return bool(self._dxl_manager._read_1_byte_at(self._id, 64))

    @torque_enabled.setter
    def torque_enabled(self, value):
        value = int(value)
        self._dxl_manager._write_1_byte_at(self._id, 64, value)
        if value:
            return

    @property
    def profile_velocity(self):
        return self._dxl_manager._read_4_bytes_at(self._id, 112)

    @profile_velocity.setter
    def profile_velocity(self, value):
        self._dxl_manager._write_4_bytes_at(self._id, 112, value)

    @property
    def profile_acceleration(self):
        return self._dxl_manager._read_4_bytes_at(self._id, 108)

    @profile_acceleration.setter
    def profile_acceleration(self, value):
        self._dxl_manager._write_4_bytes_at(self._id, 108, value)

    @property
    def goal_position(self):
        return self._dxl_manager._read_4_bytes_at(self._id, 116)

    @goal_position.setter
    def goal_position(self, value):
        # print(f"dxl{self._id}/goal position={value}")
        value = int(value)
        self._dxl_manager._write_4_bytes_at(self._id, 116, value)

    @property
    def operating_mode(self):
        return self._dxl_manager._read_1_byte_at(self._id, 11)

    @drive_mode.setter
    def operating_mode(self, value):
        """
            0x00: Position control.
            0x04: Extended position control (multi-turn).
        """
        print(f"Setting operating_mode: {self._id=}, {value=}")
        return self._dxl_manager._write_1_byte_at(self._id, 11, value)

    @property
    def is_moving(self):
        """Tell if the body is still moving."""
        return abs(self.position-self.goal_position) > self.moving_threshold

    def open(self):
        self.moving_threshold = 20

        self.torque_enabled = 0
        # Set velocity base profile.
        self.drive_mode = 0

        # set velocity and acceleration profile.
        self.profile_velocity = 40
        self.profile_acceleration = 1

        # Enable torque.
        self.torque_enabled = 1

    def move_and_wait(self, position):
        """Blocking function that sets the body's goal position and wait for it to move."""
        # self.dxl_body.torque_enabled = 1
        self.goal_position = position
        self.wait_for_servo()

    def wait_for_servo(self):
        """Blocking funtion that waits until the body has reached his goal position."""
        start = time()
        while True:
            if not self.is_moving:
                break
            assert time() - start < 30, "Moving male or female shouldn't take more than 30s!"
            timelap = time() - start