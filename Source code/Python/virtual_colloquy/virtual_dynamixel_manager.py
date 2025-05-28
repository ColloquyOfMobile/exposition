from dynamixel_sdk import COMM_SUCCESS  # Uses Dynamixel SDK library
from time import time, sleep
from threading import Thread, Lock
from pathlib import Path
from colloquy.dxl_u2d2 import DXLU2D2
from colloquy.thread_element import ThreadElement
from colloquy.logger import Logger

class VirtualPortHandler:
    def __init__(self, port_name):
        self._port_name = port_name
        pass

    def openPort(self):
        return True

    def setBaudRate(self, baudrate):
        return True

    def closePort(self):
        return

    def getPortName(self):
        return self._port_name

class VirtualDxl(ThreadElement):
    def __init__(self, owner, dxl_id):
        ThreadElement.__init__(self, name=f"dxl_{dxl_id}", owner=owner)
        # self._owner = owner
        self._dxl_id = dxl_id
        self._thread = None
        self._lock = Lock()
        self._goal_position = 0
        self._position = 0
        self._step = 10
        self._lim_min = None
        self._lim_max = None

    def __getitem__(self, key):
        if key == "position":
            return self.position
        if key == "goal position":
            return self.goal_position
        raise KeyError(f"{key=}")

    @property
    def position(self):
        return self._position

    @property
    def goal_position(self):
        return self._goal_position

    @goal_position.setter
    def goal_position(self, value):
        with self._lock:
            self._goal_position = value
            self._lim_min = value - 2*self._step
            self._lim_max = value + 2*self._step

        self.log(f"Goal position set to {self.goal_position}.")
        if self._thread is not None:
            if self._thread.is_alive():
                return
        self.start()

    def __enter__(self):
        self.stop_event.clear()

    def _loop(self):
        lim_min, lim_max  = self._lim_min, self._lim_max

        if self._lim_min < self._position < self._lim_max:
            return
            # with self._lock:
                # self._position = self.goal_position
                # self.stop_event.set()
                # return

        if self._position < self.goal_position:
            self._position += self._step
            return

        self._position -= self._step

def default_dict_init():
    return {"position":0, "goal position": 0}

class VirtualPacketHandler:
    def __init__(self, protocol):
        self._path = Path("dxl_network")
        self._name = "virtual dxl packet handler"
        self.owner = None
        self._elements = set()
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
        self.dxls = None
        self._log = Logger(owner=self)

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

class VirtualDynamixelManager(DXLU2D2):

    _classes = {
        "port_handler": VirtualPortHandler,
        "packet_handler": VirtualPacketHandler,
    }
    def __init__(self, owner, **kwargs):
        DXLU2D2.__init__(self, owner, **kwargs)
        self._dxls = {i: VirtualDxl(owner=self, dxl_id=i) for i in range(1, 11)}
        self.packet_handler.owner = self

    @property
    def dxls(self):
        return self._dxls

    def stop(self):
        for element in self.elements:
            element.stop()
        # self._dxls.clear()

    def open(self):
        DXLU2D2.open(self)
        self.packet_handler.dxls = self.dxls

    def close(self):
        DXLU2D2.close(self)
        for dxl in self.packet_handler.dxls.values():
            dxl.stop()

    def _get_com_ports(self):
        return ["VirtualCOM1", "VirtualCOM2"]