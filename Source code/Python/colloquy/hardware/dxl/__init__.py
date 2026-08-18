# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/dxl/__init__.py
from pathlib import Path
from dynamixel_sdk import (
    PortHandler,
    PacketHandler,
    COMM_SUCCESS,
)  # Uses Dynamixel SDK library
from colloquy.base import Base
from .register_handler import RegisterHanlder
from .torque_enabled import TorqueEnabled
from .goal_position import GoalPosition
from time import time, sleep


class DXL(Base):
    def __init__(self, owner, dynamixel_id):
        self._name = f"dxl_{dynamixel_id}"
        super().__init__(owner=owner)
        # Handle hardware for serial communication.
        # self.owner = owner
        self._id = dynamixel_id
        self.moving_threshold = 20
        self._old_position = None
        self._old_goal_position = None
        self._registers = []

        self["init hardware"] = self.init_hardware
        self._init_registers()
        # self.init_hardware()

    # @property
    # def goal_position(self):
    # return self._goal_position

    @property
    def u2d2(self):
        return self.owner

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def name(self):
        return self._name

    @property
    def dxl_id(self):
        return self._id

    @property
    def drive_mode(self):
        return self["drive mode"]

    @property
    def temperature(self):
        return self["temperature"]

    @property
    def elec_current(self):
        return self["elec current"]

    @property
    def position(self):
        return self["position"]

    @property
    def goal_position(self):
        return self["goal position"]

    @property
    def torque_enabled(self):
        return self["torque enabled"]

    @property
    def profile_velocity(self):
        return self["profile velocity"]

    @property
    def profile_acceleration(self):
        return self["profile acceleration"]

    @property
    def operating_mode(self):
        return self["operating mode"]

    @property
    def is_moving(self):
        """Tell if the body is still moving."""
        position = self.position.read()
        goal_position = self.goal_position.read()
        return abs(position - goal_position) > self.moving_threshold

    def move_and_wait(self, position):
        """Blocking function that sets the body's goal position and wait for it to move."""
        # self.dxl_body.torque_enabled = 1
        self.goal_position.write(position)
        self.wait_for_servo()

    # Long enough for the longest legitimate move. The bar's full travel is
    # 10000 units, and at the profile velocity init_hardware() writes (20,
    # i.e. ~313 units/s) that is about 32 seconds - so the previous 30s
    # bound could not be met by the one body that most often has to cross
    # its whole range. Simulating the servos at their configured speed is
    # what made this visible; it applies to the real bar just the same.
    MOVE_TIMEOUT = 60

    def wait_for_servo(self, timeout=None):
        """Blocking funtion that waits until the body has reached his goal position."""
        if timeout is None:
            timeout = self.MOVE_TIMEOUT
        start = time()
        while self.is_moving:
            if time() - start > timeout:
                # Raised, not asserted: asserts vanish under python -O, and
                # this is a real condition (a jammed body, a servo that lost
                # power) that the thread framework should record and show,
                # not an internal invariant.
                raise TimeoutError(
                    f"{self.name} did not reach its goal position within "
                    f"{timeout}s (position {self.position.read()}, goal "
                    f"{self.goal_position.read()})."
                )
            # Was a bare busy-loop, re-reading two registers per iteration
            # as fast as the bus allowed, for the whole length of a move.
            sleep(0.02)

    def init_hardware(self, request=None):

        self.torque_enabled.write(value=0)
        # Set velocity base profile.
        self.drive_mode.write(value=0)

        # set extended position mode.
        self.operating_mode.write(value=4)

        # set velocity and acceleration profile.
        self.profile_velocity.write(value=20)
        self.profile_acceleration.write(value=1)

        # Enable torque.
        self.torque_enabled.write(value=1)

    def _add_register(self, name, adress, readonly, byte_count, signed=False):

        if byte_count == 1:
            read = self.u2d2.read_1_byte
            write = self.u2d2.write_1_byte

        elif byte_count == 2:
            # No register uses this today ("elec current" is commented out
            # below), but leaving the branch out means uncommenting one
            # fails with an UnboundLocalError several lines later instead
            # of just working.
            read = self.u2d2._read_2_bytes_at
            write = self.u2d2._write_2_bytes_at

        elif byte_count == 4:
            read = self.u2d2.read_4_bytes
            write = self.u2d2.write_4_bytes

        else:
            raise NotImplementedError(f"{byte_count=} for register {name!r}")

        if readonly:
            write = None

        register = RegisterHanlder(
            owner=self,
            name=name,
            register=adress,
            read_func=read,
            write_func=write,
            signed=signed,
        )

        self[register.name] = register
        self._registers.append(register)

    def _init_registers(self):
        params = [
            # name,                     adress, readonly,   bytes_count, signed
            ("temperature", 146, True, 1, False),
            # ("elec current",            126     True        2       False),
            ("drive mode", 10, False, 1, False),
            # Signed: in extended position mode a position is a signed
            # 32-bit count of units from the servo's zero, and half of
            # every body's sweep sits below its origin.
            ("position", 132, True, 4, True),
            ("operating mode", 11, False, 1, False),
            ("profile velocity", 112, False, 4, False),
            ("profile acceleration", 108, False, 4, False),
            # ("torque enabled",  64,     False,      1,      False),
        ]

        for name, adress, readonly, byte_count, signed in params:
            self._add_register(
                name=name,
                adress=adress,
                readonly=readonly,
                byte_count=byte_count,
                signed=signed,
            )

        torque_enabled = TorqueEnabled(owner=self)
        self[torque_enabled.name] = torque_enabled
        self._registers.append(torque_enabled)

        goal_position = GoalPosition(owner=self)
        self[goal_position.name] = goal_position
        self._registers.append(goal_position)

    @property
    def snapshot_children(self):
        children = {}
        for register in self._registers:
            children[register.name] = register
        return children

