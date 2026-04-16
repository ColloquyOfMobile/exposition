# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/dxl/__init__.py
from pathlib import Path
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS  # Uses Dynamixel SDK library
from colloquy.base import Base
from .html import HTML
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
        
        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request        
        
        self["init hardware"] = self.init_hardware
        self._init_registers()
        # self.init_hardware()

    def __call__(self, request):
        request = Path(request)
        if not request.parts:
            raise NotImplementedError

        key, *leftover = request.parts

        if key in self:
            self[key](request="/".join(leftover))
            return

        raise NotImplementedError(f"{key=}, {leftover=}, in {self=}")

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
    def html(self):
        return self._html

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
        return abs(position-goal_position) > self.moving_threshold

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

    def init_hardware(self, request=None):

        self.torque_enabled.write(value=0)
        # Set velocity base profile.
        self.drive_mode.write(value=0)

        # set extended position mode.
        self.operating_mode.write(value=4)

        # set velocity and acceleration profile.
        self.profile_velocity.write(value=40)
        self.profile_acceleration.write(value=1)

        # Enable torque.
        self.torque_enabled.write(value=1)
    
    def _add_register(self, name, adress, readonly, byte_count):
        
        if byte_count == 1:
            read = self.u2d2.read_1_byte
            write = self.u2d2.write_1_byte
            
        elif byte_count == 4:            
            read = self.u2d2.read_4_bytes
            write = self.u2d2.write_4_bytes
        
        if readonly:
            write = None
        
        register = RegisterHanlder(
            owner=self, 
            name=name, 
            register=adress, 
            read_func=read, 
            write_func=write, 
            )
            
        self[register.name] = register
        self._registers.append(register)
        
    
    def _init_registers(self):
        params = [
            # name,                     adress, readonly,   bytes_count    
            ("temperature",             146,    True,       1),
            # ("elec current",            126     True        2),
            ("drive mode",              10,    False,      1),
            ("position",                132,    True,       4),
            ("operating mode",          11,     False,      1),
            ("profile velocity",        112,     False,      4),
            ("profile acceleration",    108,     False,      4),
            # ("torque enabled",  64,     False,      1),
        ]
        
        for name, adress, readonly, byte_count in params:
            self._add_register(name=name, adress=adress, readonly=readonly, byte_count=byte_count)
        
        torque_enabled = TorqueEnabled(owner=self)
        self[torque_enabled.name] = torque_enabled
        
        goal_position = GoalPosition(owner=self)
        self[goal_position.name] = goal_position
    
    def snapshot(self, path):
        states = super().snapshot(path=path)
        _path = states["path"]
        for register in self._registers:
            states[register.name] = register.snapshot(path=_path)
        return states
    
    