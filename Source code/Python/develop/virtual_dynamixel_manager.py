from dynamixel_sdk import COMM_SUCCESS  # Uses Dynamixel SDK library
from time import time, sleep
from threading import Thread, Lock
from colloquy_driver.dynamixel_manager import DynamixelManager
from colloquy_driver.thread_driver import ThreadDriver

class VirtualPortHandler:
    def __init__(self, port_name):
        pass

    def openPort(self):
        return True

    def setBaudRate(self, baudrate):
        return True

    def closePort(self):
        return

class VirtualDxl(ThreadDriver):
    def __init__(self, owner, dxl_id):
        ThreadDriver.__init__(self, name=f"virtual dxl {dxl_id}")
        self._owner = owner
        self._dxl_id = dxl_id
        self._thread = None
        self._lock = Lock()
        self._goal_position = 0
        self._position = 0

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
            if self._thread is None:
                self._thread = thread = Thread(target = self.run, name=self.name)
                thread.start()

    def run(self):
        goal = self.goal_position
        self.log(f"Goal position set to {goal}.")
        position = self.position
        # move_duration = 5
        step = 100
        lim_min, lim_max  = goal - 2*step, goal + 2*step
        while True:
            if self.goal_position != goal:
                self.log(f"Goal position changed to {self.goal_position}.")

            print(f"{self._dxl_id=}, {goal=}, {position=}")
            if lim_min < self._position < lim_max:
                break
            if self._position < self.goal_position:
                self._position += step
                sleep(0.1)
                continue
            self._position -= step
            sleep(0.01)

        self._position = self.goal_position

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

        self._dxls = {i: VirtualDxl(owner=self, dxl_id=i) for i in range(1, 11)}
        # print(f"{len(self._dxls)=}")

    def _write_register(self, dxl_id, value):
        pass

    def _read_register(self, dxl_id, label):
        return self._dxls[dxl_id][label]


    def _write_goal_position(self, dxl_id, value):
        self._dxls[dxl_id].goal_position = value


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