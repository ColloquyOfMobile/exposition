from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS  # Uses Dynamixel SDK library
from functools import wraps
from threading import Lock
from time import sleep


def handle_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        self = args[0]
        for i in range(3):

            with self.lock:
                value, dxl_comm_result, dxl_error = func(*args, **kwargs)
            #self._busy.clear()
            if dxl_comm_result != COMM_SUCCESS:
                print(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
                continue
            if dxl_error != 0:
                print(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")
                continue
            return value
        if dxl_comm_result != COMM_SUCCESS:
            raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        if dxl_error != 0:
            raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

    return wrapper


class DynamixelManager:

    _classes = {
        "port_handler": PortHandler,
        "packet_handler": PacketHandler,
    }

    def __init__(self, **kwargs):
        port_name = kwargs["communication port"]
        self._baudrate = kwargs["baudrate"]
        self.port_handler = self._classes["port_handler"](port_name)
        self.packet_handler = self._classes["packet_handler"](2.0)  # Using protocol 2.0
        self.lock = Lock()

    @handle_error
    def _read_1_byte_at(self, dxl_id, register_address):
        value, dxl_comm_result, dxl_error = self.packet_handler.read1ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
        )
        # if dxl_comm_result != COMM_SUCCESS:
            # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # if dxl_error != 0:
            # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

        return value, dxl_comm_result, dxl_error

    @handle_error
    def _read_2_bytes_at(self, dxl_id, register_address):
        value, dxl_comm_result, dxl_error = self.packet_handler.read2ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
        )
        # if dxl_comm_result != COMM_SUCCESS:
            # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # if dxl_error != 0:
            # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

        return value, dxl_comm_result, dxl_error

    @handle_error
    def _read_4_bytes_at(self, dxl_id, register_address):
        value, dxl_comm_result, dxl_error = self.packet_handler.read4ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
        )
        # if dxl_comm_result != COMM_SUCCESS:
            # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # if dxl_error != 0:
            # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

        return value, dxl_comm_result, dxl_error

    @handle_error
    def _write_1_byte_at(self, dxl_id, register_address, value):
        # Enable Dynamixel Torque
        dxl_comm_result, dxl_error = self.packet_handler.write1ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
            value)

        return None, dxl_comm_result, dxl_error

        # if dxl_comm_result != COMM_SUCCESS:
            # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # if dxl_error != 0:
            # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

    @handle_error
    def _write_2_bytes_at(self, dxl_id, register_address, value):
        # Enable Dynamixel Torque
        dxl_comm_result, dxl_error = self.packet_handler.write2ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
            value)

        # if dxl_comm_result != COMM_SUCCESS:
            # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # if dxl_error != 0:
            # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

        return None, dxl_comm_result, dxl_error

    @handle_error
    def _write_4_bytes_at(self, dxl_id, register_address, value):
        # Enable Dynamixel Torque
        dxl_comm_result, dxl_error = self.packet_handler.write4ByteTxRx(
            self.port_handler,
            dxl_id,
            register_address,
            value)

        return None, dxl_comm_result, dxl_error

        # if dxl_comm_result != COMM_SUCCESS:
            # raise RuntimeError(f"COM ERR: {self.packet_handler.getTxRxResult(dxl_comm_result)}")
        # if dxl_error != 0:
            # raise RuntimeError(f"DXL ERR: {self.packet_handler.getRxPacketError(dxl_error)}")

    def close(self):
        self.port_handler.closePort()


    def open(self):
        self.port_handler.openPort()
        self.port_handler.setBaudRate(self._baudrate)