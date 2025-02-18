from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS  # Uses Dynamixel SDK library
from functools import wraps
from colloquy_driver.dynamixel_manager import DynamixelManager
from time import time, sleep
from collections import defaultdict
from threading import Thread


# def handle_error(func):
    # @wraps(func)
    # def wrapper(*args, **kwargs):
        # self = args[0]
        # for i in range(3):
            # value, dxl_comm_result, dxl_error = func(*args, **kwargs)
            # if dxl_comm_result != COMM_SUCCESS:
                # print(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
                # continue
            # if dxl_error != 0:
                # print(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")
                # continue
            # return value
        # if dxl_comm_result != COMM_SUCCESS:
            # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # if dxl_error != 0:
            # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

    # return wrapper


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
        move_duration = 5
        start = time()
        while time()-start<move_duration:
            sleep(0.1)
        goal = owner._dxl_tables[self._dxl_id]["goal position"]
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
        # print(f"dxl{dxl_id}/{label}={value}")
        return COMM_SUCCESS, 0

    def write4ByteTxRx(self, port_handler, dxl_id, register_address, value):
        if register_address not in self._register_map:
            raise NotImplementedError(f"{register_address=}, {value=}")
        label = self._register_map[register_address]
        handler = self._register_writer.get(label, self._write_register)
        handler(dxl_id, value)
        # print(f"dxl{dxl_id}/{label}={value}")
        return COMM_SUCCESS, 0

    def read4ByteTxRx(self, port_handler, dxl_id, register_address):
        if register_address not in self._register_map:
            raise NotImplementedError(f"{register_address=}")
        label = self._register_map[register_address]
        handler = self._register_reader.get(label, self._read_register)
        value = handler(dxl_id, label)
        # print(f"dxl{dxl_id}/{label}(read)")
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

    # def __init__(self, **kwargs):
        # port_name = kwargs["communication port"]
        # baudrate = kwargs["baudrate"]
        # self.port_handler = self._classes["port_handler"](port_name)
        # self.packet_handler = self._classes["packet_handler"](2.0)  # Using protocol 2.0

        # if not self.port_handler.openPort():
            # raise IOError(f"Failed to open the port: {port_name}")

        # if not self.port_handler.setBaudRate(baudrate):
            # raise IOError(f"Failed to set baud rate to: {baudrate}")

    # @handle_error
    # def _read_1_byte_at(self, dxl_id, register_address):
        # value, dxl_comm_result, dxl_error = self.packet_handler.read1ByteTxRx(
            # self.port_handler,
            # dxl_id,
            # register_address,
        # )
        # # if dxl_comm_result != COMM_SUCCESS:
            # # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # # if dxl_error != 0:
            # # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

        # return value, dxl_comm_result, dxl_error

    # @handle_error
    # def _read_2_bytes_at(self, dxl_id, register_address):
        # value, dxl_comm_result, dxl_error = self.packet_handler.read2ByteTxRx(
            # self.port_handler,
            # dxl_id,
            # register_address,
        # )
        # # if dxl_comm_result != COMM_SUCCESS:
            # # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # # if dxl_error != 0:
            # # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

        # return value, dxl_comm_result, dxl_error

    # @handle_error
    # def _read_4_bytes_at(self, dxl_id, register_address):
        # value, dxl_comm_result, dxl_error = self.packet_handler.read4ByteTxRx(
            # self.port_handler,
            # dxl_id,
            # register_address,
        # )
        # # if dxl_comm_result != COMM_SUCCESS:
            # # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # # if dxl_error != 0:
            # # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

        # return value, dxl_comm_result, dxl_error

    # @handle_error
    # def _write_1_byte_at(self, dxl_id, register_address, value):
        # # Enable Dynamixel Torque
        # dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(
            # self.port_handler,
            # dxl_id,
            # register_address,
            # value)

        # return None, dxl_comm_result, dxl_error

        # # if dxl_comm_result != COMM_SUCCESS:
            # # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # # if dxl_error != 0:
            # # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

    # @handle_error
    # def _write_2_bytes_at(self, dxl_id, register_address, value):
        # # Enable Dynamixel Torque
        # dxl_comm_result, dxl_error = self.packet_handler.write2ByteTxRx(
            # self.port_handler,
            # dxl_id,
            # register_address,
            # value)

        # # if dxl_comm_result != COMM_SUCCESS:
            # # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # # if dxl_error != 0:
            # # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

        # return None, dxl_comm_result, dxl_error

    # @handle_error
    # def _write_4_bytes_at(self, dxl_id, register_address, value):
        # # Enable Dynamixel Torque
        # dxl_comm_result, dxl_error = self.packet_handler.write4ByteTxRx(
            # self.port_handler,
            # dxl_id,
            # register_address,
            # value)

        # return None, dxl_comm_result, dxl_error

        # # if dxl_comm_result != COMM_SUCCESS:
            # # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # # if dxl_error != 0:
            # # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

    # def stop(self):
        # self.port_handler.closePort()


    # def start(self):
        # self.port_handler.openPort()