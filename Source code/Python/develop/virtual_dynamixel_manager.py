from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS  # Uses Dynamixel SDK library
from functools import wraps
from colloquy_driver.dynamixel_manager import DynamixelManager
from time import time, sleep
from collections import defaultdict
from threading import Thread

class VirtualPortHandler:
    def __init__(self, port_name):
        pass

    def openPort(self):
        return True

    def setBaudRate(self, baudrate):
        return True

    def closePort(self):
        return

class DxlThread:
    def __init__(self, owner, dxl_id):
        self._owner = owner
        self._dxl_id = dxl_id

    def __call__(self):
        owner = self._owner
        table = owner._dxl_tables[self._dxl_id]
        goal = table["goal position"]
        position = table["position"]
        # move_duration = 5
        start = time()
        step = 100
        lim_min, lim_max  = goal - 2*step, goal + 2*step
        while True:
            if lim_min < table["position"] < lim_max:
                break
            if table["position"] < goal:
                table["position"] += step
                sleep(0.1)
                continue
            table["position"] -= step
            sleep(0.01)

        owner._dxl_tables[self._dxl_id]["position"] = goal

def default_dict_init():
    return {"position":0, "goal position": 0}

class VirtualPacketHandler:
    def __init__(self, protocol):
        self._dxl_threads = {}
        self._register_map = {
            64: "torque",
            10: "drive mode",
            11: "operating mode",
            112: "profile velocity",
            108: "profile acceleration",
            132: "position",
            116: "goal position",
            }
        self._register_writer = {
            "goal position": self._write_goal_position
        }
        self._register_reader = {
        }
        self._dxl_tables = defaultdict(default_dict_init)

    def _write_register(self, dxl_id, value):
        pass

    def _read_register(self, dxl_id, label):
        return self._dxl_tables[dxl_id][label]


    def _write_goal_position(self, dxl_id, value):
        self._dxl_tables[dxl_id]["goal position"] = value
        Thread(target = DxlThread(owner=self, dxl_id=dxl_id)).start()


    def write1ByteTxRx(self, port_handler, dxl_id, register_address, value):
        if register_address not in self._register_map:
            raise NotImplementedError(f"{register_address=}, {value=}")
        label = self._register_map[register_address]
        handler = self._register_writer.get(label, self._write_register)
        handler(dxl_id, value)
        return COMM_SUCCESS, 0

    def write4ByteTxRx(self, port_handler, dxl_id, register_address, value):
        if register_address not in self._register_map:
            raise NotImplementedError(f"{register_address=}, {value=}")
        label = self._register_map[register_address]
        handler = self._register_writer.get(label, self._write_register)
        handler(dxl_id, value)
        return COMM_SUCCESS, 0

    def read4ByteTxRx(self, port_handler, dxl_id, register_address):
        if register_address not in self._register_map:
            raise NotImplementedError(f"{register_address=}")
        label = self._register_map[register_address]
        handler = self._register_reader.get(label, self._read_register)
        value = handler(dxl_id, label)
        return value, COMM_SUCCESS, 0

    def getTxRxResult(self, result):
        raise NotImplementedError
        return None

    def getRxPacketError(self, result):
        raise NotImplementedError
        return None

class VirtualDynamixelManager(DynamixelManager):

    _classes = {
        "port_handler": VirtualPortHandler,
        "packet_handler": VirtualPacketHandler,
    }