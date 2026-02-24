from dynamixel_sdk import COMM_SUCCESS  # Uses Dynamixel SDK library
from time import time, sleep
from threading import Thread, Lock
from pathlib import Path
from colloquy.base import Base
from .virtual_dxl import VirtualDXL

_1_BYTE_REGISTERS = {
    "drive mode",
    "temperature",
    "torque enabled",
    "operating mode"
}
_4_BYTE_REGISTERS = {
    "position",
    "goal position",
    "profile velocity",
    "profile acceleration",
}


# class VirtualDXL(Base):
    
    # def __init__(self, owner):
        # super().__init__(owner=owner)
        # self._dict = {
            # "drive mode": None,
            # "temperature": 25,
            # }
    
    # def get(self, label):
        # return self._dict[label]
    
    # def set(self, label, value):
        # self._dict[label] = value

    
class VirtualPacketHandler(Base):
    def __init__(self, protocol):
        super().__init__(owner=None)
        self._path = Path("dxl_network")
        self._name = "virtual dxl packet handler"
        self._elements = set()
        self._register_map = {
            64: "torque enabled",
            10: "drive mode",
            11: "operating mode",
            112: "profile velocity",
            108: "profile acceleration",
            132: "position",
            116: "goal position",
            146: "temperature",
            }
        self._register_reader = {
        }
        self._dxls = [
            VirtualDXL(owner=self, dxl_id=i)
            for i
            in range(10)
        ]

    @property
    def name(self):
        return self._name

    @property
    def log(self):
        return self._log

    @property
    def elements(self):
        return self._elements

    @property
    def path(self):
        return self._path

    def _write_register(self, dxl_id, value):
        pass

    def _read_register(self, dxl_id, label):
        return self.dxls[dxl_id][label]


    def _write_goal_position(self, dxl_id, value):
        self.log(f"Write goal position {value=} to dxl{dxl_id=}")
        self.dxls[dxl_id].goal_position = value

    def write1ByteTxRx(self, port_handler, dxl_id, register_address, value):            
        label = self._register_map[register_address]        
        assert label in _1_BYTE_REGISTERS, f"{label=}, {value=}"            
        value = self._dxls[dxl_id].set(label, value)
        return COMM_SUCCESS, 0

    def read1ByteTxRx(self, port_handler, dxl_id, register_address):          
        label = self._register_map[register_address]
        assert label in _1_BYTE_REGISTERS, f"{label=}, {value=}"
        value = self._dxls[dxl_id].get(label)        
        return value, COMM_SUCCESS, 0

    def write4ByteTxRx(self, port_handler, dxl_id, register_address, value):          
        label = self._register_map[register_address]        
        assert label in _4_BYTE_REGISTERS, f"{label=}, {value=}"            
        value = self._dxls[dxl_id].set(label, value)
        return COMM_SUCCESS, 0

    def read4ByteTxRx(self, port_handler, dxl_id, register_address):     
        label = self._register_map[register_address]
        assert label in _4_BYTE_REGISTERS, f"{label=}, {value=}"
        value = self._dxls[dxl_id].get(label)        
        return value, COMM_SUCCESS, 0

    def getTxRxResult(self, result):
        raise NotImplementedError
        return None

    def getRxPacketError(self, result):
        raise NotImplementedError
        return None

